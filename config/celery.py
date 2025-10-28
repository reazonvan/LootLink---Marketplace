"""
Конфигурация Celery для асинхронных задач.
"""
import os
from celery import Celery
from django.conf import settings

# Устанавливаем настройки Django для Celery
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Создаем приложение Celery
app = Celery('lootlink')

# Загружаем конфигурацию из Django settings с префиксом CELERY_
app.config_from_object('django.conf:settings', namespace='CELERY')

# Автоматически находим задачи в приложениях
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    """Тестовая задача для проверки работоспособности Celery."""
    print(f'Request: {self.request!r}')

