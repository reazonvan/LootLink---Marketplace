"""
Celery задачи для экспорта данных.
"""
from celery import shared_task
from django.conf import settings
from django.utils import timezone
from django.core.mail import send_mail
import os
import json
import zipfile
from io import BytesIO
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def generate_data_export(self, export_request_id):
    """
    Генерирует ZIP архив с данными пользователя.
    """
    from accounts.models_export import DataExportRequest
    from accounts.views_export import generate_export_data

    try:
        export_request = DataExportRequest.objects.get(id=export_request_id)
        export_request.status = 'processing'
        export_request.save()

        user = export_request.user

        # Генерируем данные
        data = generate_export_data(user)

        # Создаем директорию для экспортов
        export_dir = os.path.join(settings.MEDIA_ROOT, 'exports')
        os.makedirs(export_dir, exist_ok=True)

        # Создаем ZIP файл
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        zip_filename = f'export_{user.username}_{timestamp}.zip'
        zip_path = os.path.join(export_dir, zip_filename)

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Добавляем JSON с данными
            json_data = json.dumps(data, ensure_ascii=False, indent=2)
            zipf.writestr('data.json', json_data)

            # Добавляем README
            readme = """# Экспорт данных LootLink

Этот архив содержит все ваши данные с платформы LootLink.

## Содержимое:
- data.json - все ваши данные в формате JSON

## Структура данных:
- user - информация об аккаунте
- profile - данные профиля
- listings - ваши объявления
- favorites - избранные объявления
- purchases - история покупок
- sales - история продаж
- reviews_given - оставленные отзывы
- reviews_received - полученные отзывы
- messages - история сообщений

Этот файл действителен в течение 7 дней с момента создания.
"""
            zipf.writestr('README.txt', readme)

        # Обновляем запрос
        export_request.status = 'completed'
        export_request.file_path = zip_path
        export_request.completed_at = timezone.now()
        export_request.save()

        # Отправляем email
        send_mail(
            subject='Ваш экспорт данных готов - LootLink',
            message=f'''Здравствуйте, {user.username}!

Ваш запрос на экспорт данных обработан.

Скачать архив: {settings.SITE_URL}/accounts/data-export/download/{export_request.id}/

Ссылка действительна в течение 7 дней.

С уважением,
Команда LootLink''',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False
        )

        logger.info(f'Data export completed for user {user.username}')
        return f'Export completed: {zip_filename}'

    except Exception as exc:
        logger.error(f'Data export failed: {str(exc)}')

        try:
            export_request.status = 'failed'
            export_request.error_message = str(exc)
            export_request.save()
        except Exception:
            pass

        raise self.retry(exc=exc, countdown=60)


@shared_task
def cleanup_old_exports():
    """
    Удаляет старые файлы экспорта (старше 7 дней).
    """
    from accounts.models_export import DataExportRequest
    import os

    threshold = timezone.now() - timezone.timedelta(days=7)
    old_exports = DataExportRequest.objects.filter(
        status='completed',
        created_at__lt=threshold
    )

    deleted_count = 0
    for export in old_exports:
        if export.file_path and os.path.exists(export.file_path):
            try:
                os.remove(export.file_path)
                deleted_count += 1
            except Exception as e:
                logger.error(f'Failed to delete export file: {e}')

        export.delete()

    logger.info(f'Cleaned up {deleted_count} old export files')
    return f'Deleted {deleted_count} old exports'
