"""
Селекторы для `accounts/` — слой чтения из БД.

Селекторы:
- Только читают данные (без mutations).
- Используют `select_related`/`prefetch_related` для оптимизации.
- Возвращают QuerySet или модель, не HttpResponse.

См. HackSoft styleguide: https://github.com/HackSoftware/Django-Styleguide#selectors

ВАЖНО: этот файл создан как скелет в рамках P3 рефакторинга.
"""

from typing import Optional

from django.contrib.auth import get_user_model
from django.db.models import QuerySet

CustomUser = get_user_model()


def user_get_by_username(*, username: str) -> Optional["CustomUser"]:
    """Получить пользователя по username (case-insensitive)."""
    return CustomUser.objects.filter(username__iexact=username).select_related("profile").first()


def user_list_verified() -> "QuerySet[CustomUser]":
    """Список верифицированных пользователей с подгруженным profile."""
    return CustomUser.objects.filter(profile__is_verified=True).select_related("profile")
