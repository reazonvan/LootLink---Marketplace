"""
Асинхронные задачи Celery для core приложения.
"""

from typing import List

from django.conf import settings
from django.core.mail import send_mail

from celery import shared_task


@shared_task(bind=True, max_retries=3)
def send_email_async(self, subject: str, message: str, recipient: str):
    """
    Асинхронная отправка email.

    Args:
        subject: Тема письма
        message: Текст письма
        recipient: Email получателя
    """
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient],
            fail_silently=False,
        )
        return f"Email успешно отправлен на {recipient}"
    except Exception as exc:
        # Повторная попытка через 30 секунд
        raise self.retry(exc=exc, countdown=30)


@shared_task
def send_bulk_emails_async(subject: str, message: str, recipients: List[str]):
    """
    Асинхронная отправка email нескольким получателям.

    Args:
        subject: Тема письма
        message: Текст письма
        recipients: Список email получателей
    """
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipients,
            fail_silently=False,
        )
        return f"Emails отправлены {len(recipients)} получателям"
    except Exception as e:
        return f"Ошибка отправки: {str(e)}"


@shared_task
def cleanup_old_data():
    """
    Периодическая задача для очистки старых данных.
    Удаляет:
    - Истекшие коды сброса пароля (старше 24 часов)
    - Неиспользованные токены верификации (старше 7 дней)
    - Старые уведомления (прочитанные, старше 30 дней)
    """
    from datetime import timedelta

    from django.utils import timezone

    from accounts.models import EmailVerification, PasswordResetCode
    from core.models import Notification

    now = timezone.now()

    # Удаляем старые коды сброса пароля
    old_codes = PasswordResetCode.objects.filter(created_at__lt=now - timedelta(hours=24))
    codes_deleted = old_codes.count()
    old_codes.delete()

    # Удаляем старые неверифицированные токены
    old_verifications = EmailVerification.objects.filter(
        is_verified=False, created_at__lt=now - timedelta(days=7)
    )
    verifications_deleted = old_verifications.count()
    old_verifications.delete()

    # Удаляем старые прочитанные уведомления
    old_notifications = Notification.objects.filter(
        is_read=True, created_at__lt=now - timedelta(days=30)
    )
    notifications_deleted = old_notifications.count()
    old_notifications.delete()

    return {
        "codes_deleted": codes_deleted,
        "verifications_deleted": verifications_deleted,
        "notifications_deleted": notifications_deleted,
    }


@shared_task
def update_user_ratings():
    """Массовое обновление рейтингов одним SQL.

    P1-18: было N select_for_update + AVG для каждого пользователя.
    Теперь — один UPDATE с подзапросом-агрегатом.
    """
    from django.db import connection

    if connection.vendor == "postgresql":
        sql = """
        UPDATE accounts_profile p
        SET rating = COALESCE(sub.avg_rating, 0)
        FROM (
            SELECT reviewed_user_id, ROUND(AVG(rating)::numeric, 2) AS avg_rating
            FROM transactions_review
            GROUP BY reviewed_user_id
        ) AS sub
        WHERE sub.reviewed_user_id = p.user_id;
        """
        with connection.cursor() as cursor:
            cursor.execute(sql)
        # Обнуляем рейтинг у тех, у кого вообще нет отзывов
        from accounts.models import Profile
        from transactions.models import Review

        Profile.objects.exclude(user_id__in=Review.objects.values("reviewed_user_id")).update(
            rating=0
        )
        return "Рейтинги обновлены одним UPDATE (PostgreSQL)"

    # Fallback для SQLite/dev — итеративно
    from accounts.models import Profile

    profiles = Profile.objects.all().iterator(chunk_size=200)
    updated_count = 0
    errors_count = 0
    for profile in profiles:
        try:
            profile.update_rating()
            updated_count += 1
        except Exception as e:
            errors_count += 1
            import logging

            logging.getLogger(__name__).error(
                f"Ошибка обновления рейтинга для {profile.user.username}: {e}"
            )
    return f"Обновлено рейтингов: {updated_count}, ошибок: {errors_count}"


@shared_task
def cleanup_security_audit_logs(days=90):
    """
    Очистка старых логов аудита безопасности.
    По умолчанию удаляет логи старше 90 дней.

    Args:
        days: Количество дней для хранения логов
    """
    from datetime import timedelta

    from django.utils import timezone

    from .models_audit import SecurityAuditLog

    threshold = timezone.now() - timedelta(days=days)
    deleted_count, _ = SecurityAuditLog.objects.filter(created_at__lt=threshold).delete()
    return f"Удалено {deleted_count} записей audit log старше {days} дней"


@shared_task
def cleanup_login_attempts(days=30):
    """
    Очистка старых попыток входа.
    По умолчанию удаляет попытки старше 30 дней.

    Args:
        days: Количество дней для хранения записей
    """
    from datetime import timedelta

    from django.utils import timezone

    from .models_audit import SecurityAuditLog

    threshold = timezone.now() - timedelta(days=days)
    deleted_count, _ = SecurityAuditLog.objects.filter(
        action_type="login_failed",
        created_at__lt=threshold,
    ).delete()
    return f"Удалено {deleted_count} записей неудачных входов старше {days} дней"
