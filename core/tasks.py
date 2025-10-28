"""
Асинхронные задачи Celery для core приложения.
"""
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from typing import List


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
            fail_silently=False
        )
        return f'Email успешно отправлен на {recipient}'
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
            fail_silently=False
        )
        return f'Emails отправлены {len(recipients)} получателям'
    except Exception as e:
        return f'Ошибка отправки: {str(e)}'


@shared_task
def cleanup_old_data():
    """
    Периодическая задача для очистки старых данных.
    Удаляет:
    - Истекшие коды сброса пароля (старше 24 часов)
    - Неиспользованные токены верификации (старше 7 дней)
    - Старые уведомления (прочитанные, старше 30 дней)
    """
    from django.utils import timezone
    from datetime import timedelta
    from accounts.models import PasswordResetCode, EmailVerification
    from core.models import Notification
    
    now = timezone.now()
    
    # Удаляем старые коды сброса пароля
    old_codes = PasswordResetCode.objects.filter(
        created_at__lt=now - timedelta(hours=24)
    )
    codes_deleted = old_codes.count()
    old_codes.delete()
    
    # Удаляем старые неверифицированные токены
    old_verifications = EmailVerification.objects.filter(
        is_verified=False,
        created_at__lt=now - timedelta(days=7)
    )
    verifications_deleted = old_verifications.count()
    old_verifications.delete()
    
    # Удаляем старые прочитанные уведомления
    old_notifications = Notification.objects.filter(
        is_read=True,
        created_at__lt=now - timedelta(days=30)
    )
    notifications_deleted = old_notifications.count()
    old_notifications.delete()
    
    return {
        'codes_deleted': codes_deleted,
        'verifications_deleted': verifications_deleted,
        'notifications_deleted': notifications_deleted
    }


@shared_task
def update_user_ratings():
    """
    Периодическая задача для обновления рейтингов всех пользователей.
    Запускается раз в час для поддержания актуальности рейтингов.
    """
    from accounts.models import Profile
    
    profiles = Profile.objects.all()
    updated_count = 0
    
    for profile in profiles:
        try:
            profile.update_rating()
            updated_count += 1
        except Exception as e:
            print(f'Ошибка обновления рейтинга для {profile.user.username}: {e}')
    
    return f'Обновлено рейтингов: {updated_count}'

