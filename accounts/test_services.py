"""Тесты для accounts/services.py — user_register."""

from django.contrib.auth import get_user_model

import pytest

from accounts.services import user_register

CustomUser = get_user_model()


@pytest.mark.django_db
def test_user_register_creates_user_with_profile():
    """Регистрация создаёт пользователя; сигнал post_save поднимает Profile."""
    user = user_register(
        username="newuser",
        email="new@example.com",
        password="StrongPass123!",  # nosec B106 — фикстура для теста
    )

    assert user.pk is not None
    assert user.username == "newuser"
    assert user.email == "new@example.com"
    assert user.check_password("StrongPass123!")
    # Профиль создаётся сигналом
    assert hasattr(user, "profile")


@pytest.mark.django_db
def test_user_register_sets_phone_when_provided():
    """Если передан phone — пишется в profile.phone."""
    user = user_register(
        username="phonedup",
        email="phone@example.com",
        password="StrongPass123!",  # nosec B106 — фикстура для теста
        phone="+71234567890",
    )

    assert user.profile.phone == "+71234567890"


@pytest.mark.django_db
def test_user_register_without_phone_leaves_blank():
    """Без phone profile.phone остаётся пустым (или дефолтным)."""
    user = user_register(
        username="nophone",
        email="nophone@example.com",
        password="StrongPass123!",  # nosec B106 — фикстура для теста
    )

    # phone — CharField с blank=True; ожидаем пустую строку
    assert user.profile.phone in ("", None)
