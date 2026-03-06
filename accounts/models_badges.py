"""
Система бейджей для пользователей.
Расширение для Profile модели.

ВАЖНО: Все бейджи основаны на заслугах и активности.
Никаких платных преимуществ - все пользователи равны.
"""
from django.utils import timezone
from datetime import timedelta


def get_user_badges(profile):
    """
    Возвращает список бейджей пользователя для отображения.

    Все бейджи заслуживаются через активность и качество работы.
    Нет платных преимуществ.

    Args:
        profile: Profile объект пользователя

    Returns:
        list: Список словарей с информацией о бейджах
    """
    badges = []

    # Верифицированный пользователь
    if profile.is_verified:
        badges.append({
            'icon': 'bi-patch-check-fill',
            'text': 'Верифицирован',
            'color': 'success',
            'tooltip': 'Подтвержден email и телефон'
        })

    # Топ продавец (рейтинг >= 4.8 и >= 50 продаж)
    if profile.rating >= 4.8 and profile.total_sales >= 50:
        badges.append({
            'icon': 'bi-star-fill',
            'text': 'Топ продавец',
            'color': 'warning',
            'tooltip': 'Высокий рейтинг и опыт'
        })

    # Активный (онлайн сейчас)
    if profile.get_online_status() == 'online':
        badges.append({
            'icon': 'bi-circle-fill',
            'text': 'Онлайн',
            'color': 'danger',
            'tooltip': 'Сейчас на сайте'
        })

    # Новичок (аккаунт создан менее 30 дней назад)
    if profile.created_at > timezone.now() - timedelta(days=30):
        badges.append({
            'icon': 'bi-person-plus-fill',
            'text': 'Новичок',
            'color': 'info',
            'tooltip': 'Недавно зарегистрирован'
        })

    # Опытный продавец (10+ продаж, но меньше 50)
    if 10 <= profile.total_sales < 50:
        badges.append({
            'icon': 'bi-briefcase-fill',
            'text': 'Опытный',
            'color': 'primary',
            'tooltip': f'{profile.total_sales} успешных продаж'
        })

    # Модератор
    if profile.is_moderator:
        badges.append({
            'icon': 'bi-shield-fill',
            'text': 'Модератор',
            'color': 'dark',
            'tooltip': 'Модератор платформы'
        })

    return badges


# Добавляем метод к Profile через monkey patching
def add_badges_method():
    """
    Добавляет метод get_badges к Profile модели.
    Вызывается в apps.py при инициализации приложения.
    """
    from accounts.models import Profile
    Profile.get_badges = lambda self: get_user_badges(self)
