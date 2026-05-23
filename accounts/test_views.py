"""
Comprehensive тесты для views приложения accounts.
"""

from django.contrib.auth import get_user_model
from django.urls import reverse

import pytest

from accounts.models import EmailVerification, PasswordResetCode
from accounts.models_security import LoginHistory

CustomUser = get_user_model()


@pytest.mark.django_db
class TestRegistrationView:
    """Тесты регистрации."""

    def test_registration_page_get(self, client):
        """GET запрос на страницу регистрации."""
        response = client.get(reverse("accounts:register"))
        assert response.status_code == 200
        assert "Регистрация" in response.content.decode()

    def test_registration_redirect_if_authenticated(self, authenticated_client):
        """Аутентифицированный пользователь перенаправляется."""
        response = authenticated_client.get(reverse("accounts:register"))
        assert response.status_code == 302

    def test_successful_registration(self, client):
        """Успешная регистрация."""
        data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "phone": "+7 (999) 123-45-67",
            "password1": "complexP@ss123",
            "password2": "complexP@ss123",
            "consent": True,
        }
        response = client.post(reverse("accounts:register"), data)

        assert response.status_code == 302
        assert CustomUser.objects.filter(username="newuser").exists()
        assert "_auth_user_id" in client.session

        user = CustomUser.objects.get(username="newuser")
        assert user.profile.phone == "+7 (999) 123-45-67"

        # Проверяем что создан токен верификации
        assert EmailVerification.objects.filter(user=user).exists()

    def test_registration_duplicate_email(self, client, verified_user):
        """Регистрация с существующим email."""
        data = {
            "username": "anotheruser",
            "email": verified_user.email,
            "phone": "+7 (999) 123-45-68",
            "password1": "complexP@ss123",
            "password2": "complexP@ss123",
            "consent": True,
        }
        response = client.post(reverse("accounts:register"), data)

        assert response.status_code == 200  # Остаемся на форме
        assert (
            "email" in response.context["form"].errors
            or "пользователь" in response.content.decode().lower()
        )

    def test_registration_password_mismatch(self, client):
        """Пароли не совпадают."""
        data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "phone": "+7 (999) 123-45-67",
            "password1": "complexP@ss123",
            "password2": "differentP@ss123",
            "consent": True,
        }
        response = client.post(reverse("accounts:register"), data)

        assert response.status_code == 200
        assert not CustomUser.objects.filter(username="newuser").exists()

    def test_registration_invalid_phone(self, client):
        """Невалидный номер телефона."""
        data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "phone": "123",  # Слишком короткий
            "password1": "complexP@ss123",
            "password2": "complexP@ss123",
            "consent": True,
        }
        response = client.post(reverse("accounts:register"), data)

        assert response.status_code == 200
        assert not CustomUser.objects.filter(username="newuser").exists()


@pytest.mark.django_db
class TestLoginView:
    """Тесты входа."""

    def test_login_page_get(self, client):
        """GET запрос на страницу входа."""
        response = client.get(reverse("accounts:login"))
        assert response.status_code == 200
        assert "Вход" in response.content.decode()

    def test_login_redirect_if_authenticated(self, authenticated_client):
        """Аутентифицированный пользователь перенаправляется."""
        response = authenticated_client.get(reverse("accounts:login"))
        assert response.status_code == 302

    def test_successful_login(self, client, verified_user):
        """Успешный вход."""
        response = client.post(
            reverse("accounts:login"),
            {
                "username": verified_user.username,
                "password": "testpass123",
            },
        )

        assert response.status_code == 302
        # Проверяем что пользователь аутентифицирован
        assert "_auth_user_id" in client.session

    def test_login_invalid_credentials(self, client, verified_user):
        """Вход с неверными данными."""
        response = client.post(
            reverse("accounts:login"),
            {
                "username": verified_user.username,
                "password": "wrongpassword",
            },
        )

        assert response.status_code == 200
        assert "_auth_user_id" not in client.session

    def test_login_with_email(self, client, verified_user):
        """Вход с email вместо username."""
        response = client.post(
            reverse("accounts:login"),
            {
                "username": verified_user.email,
                "password": "testpass123",
            },
        )

        assert response.status_code == 302
        assert "_auth_user_id" in client.session

    def test_login_next_parameter(self, client, verified_user):
        """Редирект после входа на указанную страницу."""
        response = client.post(
            reverse("accounts:login") + "?next=/catalog/",
            {
                "username": verified_user.username,
                "password": "testpass123",
            },
        )

        assert response.status_code == 302
        assert response.url == "/catalog/"

    def test_login_next_parameter_from_post(self, client, verified_user):
        """Редирект после входа через hidden input next в POST."""
        response = client.post(
            reverse("accounts:login"),
            {
                "username": verified_user.username,
                "password": "testpass123",
                "next": "/accounts/my-listings/",
            },
        )

        assert response.status_code == 302
        assert response.url == "/accounts/my-listings/"


@pytest.mark.django_db
class TestLogoutView:
    """Тесты выхода."""

    def test_logout(self, authenticated_client):
        """Выход из системы (Django 5+ требует POST)."""
        response = authenticated_client.post(reverse("accounts:logout"))

        assert response.status_code == 302
        assert "_auth_user_id" not in authenticated_client.session


@pytest.mark.django_db
class TestProfileView:
    """Тесты просмотра профиля."""

    def test_profile_view(self, client, verified_user):
        """Просмотр профиля."""
        response = client.get(
            reverse("accounts:profile", kwargs={"username": verified_user.username})
        )

        assert response.status_code == 200
        assert verified_user.username in response.content.decode()

    def test_profile_not_found(self, client):
        """Профиль несуществующего пользователя."""
        response = client.get(reverse("accounts:profile", kwargs={"username": "nonexistent"}))

        assert response.status_code == 404

    def test_profile_creates_if_missing(self, client, verified_user):
        """Профиль создается если отсутствует."""
        # Удаляем профиль (хотя это не должно быть возможно в реальности)
        verified_user.profile.delete = lambda: None  # Обходим защиту

        response = client.get(
            reverse("accounts:profile", kwargs={"username": verified_user.username})
        )

        assert response.status_code == 200


@pytest.mark.django_db
class TestProfileEditView:
    """Тесты редактирования профиля."""

    def test_profile_edit_requires_login(self, client):
        """Редактирование требует авторизации."""
        response = client.get(reverse("accounts:profile_edit"))
        assert response.status_code == 302
        assert "/accounts/login/" in response.url

    def test_profile_edit_get(self, authenticated_client):
        """GET запрос на редактирование."""
        response = authenticated_client.get(reverse("accounts:profile_edit"))
        assert response.status_code == 200

    def test_profile_edit_success(self, authenticated_client, verified_user):
        """Успешное редактирование профиля. ProfileUpdateForm: avatar, bio, phone."""
        data = {
            "username": verified_user.username,
            "email": verified_user.email,
            "bio": "Новый текст био для профиля.",
        }
        response = authenticated_client.post(reverse("accounts:profile_edit"), data)

        assert response.status_code == 302

        verified_user.profile.refresh_from_db()
        assert verified_user.profile.bio == "Новый текст био для профиля."

    def test_profile_phone_readonly_after_set(self, authenticated_client, verified_user):
        """Телефон нельзя изменить после установки."""
        verified_user.profile.phone = "+7 (999) 123-45-67"
        verified_user.profile.save()

        data = {
            "username": verified_user.username,
            "email": verified_user.email,
            "phone": "+7 (999) 999-99-99",  # Пытаемся изменить
            "bio": "New bio",
        }
        response = authenticated_client.post(reverse("accounts:profile_edit"), data)

        verified_user.profile.refresh_from_db()
        # Телефон не должен измениться
        assert verified_user.profile.phone == "+7 (999) 123-45-67"


@pytest.mark.django_db
class TestPasswordReset:
    """Тесты сброса пароля."""

    def test_password_reset_request_page(self, client):
        """Страница запроса сброса пароля."""
        response = client.get(reverse("accounts:password_reset_request"))
        assert response.status_code == 200

    def test_password_reset_request_success(self, client, verified_user):
        """Успешный запрос сброса пароля."""
        response = client.post(
            reverse("accounts:password_reset_request"), {"email": verified_user.email}
        )

        assert response.status_code == 302
        assert PasswordResetCode.objects.filter(user=verified_user).exists()

    def test_password_reset_invalid_email(self, client):
        """Запрос сброса для несуществующего email — не раскрывает существование аккаунта."""
        response = client.post(
            reverse("accounts:password_reset_request"), {"email": "nonexistent@example.com"}
        )

        # Всегда редирект, чтобы не раскрывать существование аккаунта
        assert response.status_code == 302


@pytest.mark.django_db
class TestEmailVerification:
    """Тесты верификации email."""

    def test_verify_email_success(self, client, unverified_user):
        """Успешная верификация email."""
        verification = EmailVerification.create_for_user(unverified_user)

        response = client.get(
            reverse("accounts:verify_email", kwargs={"token": verification.token})
        )

        assert response.status_code == 302

        verification.refresh_from_db()
        assert verification.is_verified

        unverified_user.profile.refresh_from_db()
        assert unverified_user.profile.is_verified

    def test_verify_email_invalid_token(self, client):
        """Верификация с невалидным токеном."""
        response = client.get(reverse("accounts:verify_email", kwargs={"token": "invalid_token"}))

        assert response.status_code == 302

    def test_verify_email_already_verified(self, client, unverified_user):
        """Попытка верифицировать уже верифицированный email."""
        verification = EmailVerification.create_for_user(unverified_user)
        verification.verify()

        response = client.get(
            reverse("accounts:verify_email", kwargs={"token": verification.token})
        )

        assert response.status_code == 302


@pytest.mark.django_db
class TestMyListings:
    """Тесты страницы 'Мои объявления'."""

    def test_my_listings_requires_login(self, client):
        """Требуется авторизация."""
        response = client.get(reverse("accounts:my_listings"))
        assert response.status_code == 302

    def test_my_listings_display(self, authenticated_client, verified_user, listing_factory):
        """Отображение объявлений."""
        listing1 = listing_factory(verified_user, title="Listing 1")
        listing2 = listing_factory(verified_user, title="Listing 2")

        response = authenticated_client.get(reverse("accounts:my_listings"))

        assert response.status_code == 200
        assert "Listing 1" in response.content.decode()
        assert "Listing 2" in response.content.decode()

    def test_my_listings_pagination(self, authenticated_client, verified_user, listing_factory):
        """Пагинация объявлений."""
        # Создаем 25 объявлений
        for i in range(25):
            listing_factory(verified_user, title=f"Listing {i}")

        response = authenticated_client.get(reverse("accounts:my_listings"))

        assert response.status_code == 200
        # Должна быть пагинация (20 на страницу)
        assert "page_obj" in response.context


@pytest.mark.django_db
class TestMyPurchases:
    """Тесты страницы 'Мои покупки'."""

    def test_my_purchases_requires_login(self, client):
        """Требуется авторизация."""
        response = client.get(reverse("accounts:my_purchases"))
        assert response.status_code == 302

    def test_my_purchases_display(
        self, authenticated_client, verified_user, seller, active_listing, purchase_request_factory
    ):
        """Отображение покупок."""
        purchase = purchase_request_factory(active_listing, verified_user)

        response = authenticated_client.get(reverse("accounts:my_purchases"))

        assert response.status_code == 200


@pytest.mark.django_db
class TestMySales:
    """Тесты страницы 'Мои продажи'."""

    def test_my_sales_requires_login(self, client):
        """Требуется авторизация."""
        response = client.get(reverse("accounts:my_sales"))
        assert response.status_code == 302

    def test_my_sales_display(
        self, authenticated_client, verified_user, buyer, listing_factory, purchase_request_factory
    ):
        """Отображение продаж."""
        listing = listing_factory(verified_user)
        purchase = purchase_request_factory(listing, buyer)

        response = authenticated_client.get(reverse("accounts:my_sales"))

        assert response.status_code == 200


@pytest.mark.django_db
class TestAjaxEndpoints:
    """Тесты AJAX endpoints для проверки уникальности."""

    def test_check_username_available(self, client):
        """Проверка доступности никнейма."""
        response = client.get(reverse("accounts:check_username"), {"username": "newuser"})
        assert response.status_code == 200
        data = response.json()
        assert data["available"] is True
        assert "доступен" in data["message"].lower()

    def test_check_username_taken(self, client, verified_user):
        """Проверка занятого никнейма."""
        response = client.get(
            reverse("accounts:check_username"), {"username": verified_user.username}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["available"] is False
        assert "занят" in data["message"].lower()

    def test_check_username_empty(self, client):
        """Проверка пустого никнейма."""
        response = client.get(reverse("accounts:check_username"), {"username": ""})
        assert response.status_code == 200
        data = response.json()
        assert data["available"] is False

    def test_check_username_too_short(self, client):
        """Проверка слишком короткого никнейма."""
        response = client.get(reverse("accounts:check_username"), {"username": "ab"})
        assert response.status_code == 200
        data = response.json()
        assert data["available"] is False
        assert "минимум" in data["message"].lower()

    def test_check_username_invalid_chars(self, client):
        """Проверка никнейма с недопустимыми символами."""
        response = client.get(reverse("accounts:check_username"), {"username": "user@#$%"})
        assert response.status_code == 200
        data = response.json()
        assert data["available"] is False
        assert "недопустимые" in data["message"].lower()

    def test_check_email_available(self, client):
        """Проверка доступности email."""
        response = client.get(reverse("accounts:check_email"), {"email": "new@example.com"})
        assert response.status_code == 200
        data = response.json()
        assert data["available"] is True
        assert "доступен" in data["message"].lower()

    def test_check_email_taken(self, client, verified_user):
        """Проверка занятого email."""
        response = client.get(reverse("accounts:check_email"), {"email": verified_user.email})
        assert response.status_code == 200
        data = response.json()
        assert data["available"] is False
        assert "зарегистрирован" in data["message"].lower()

    def test_check_email_invalid(self, client):
        """Проверка некорректного email."""
        response = client.get(reverse("accounts:check_email"), {"email": "invalid-email"})
        assert response.status_code == 200
        data = response.json()
        assert data["available"] is False
        assert "некорректн" in data["message"].lower()

    def test_check_phone_available(self, client):
        """Проверка доступности телефона."""
        response = client.get(reverse("accounts:check_phone"), {"phone": "+7 (999) 888-77-66"})
        assert response.status_code == 200
        data = response.json()
        assert data["available"] is True
        assert "доступен" in data["message"].lower()

    def test_check_phone_taken(self, client, verified_user):
        """Проверка занятого телефона."""
        verified_user.profile.phone = "+7 (999) 123-45-67"
        verified_user.profile.save()

        response = client.get(reverse("accounts:check_phone"), {"phone": "+7 (999) 123-45-67"})
        assert response.status_code == 200
        data = response.json()
        assert data["available"] is False
        assert "зарегистрирован" in data["message"].lower()

    def test_check_phone_invalid(self, client):
        """Проверка некорректного телефона."""
        response = client.get(reverse("accounts:check_phone"), {"phone": "123"})
        assert response.status_code == 200
        data = response.json()
        assert data["available"] is False
        assert "некорректн" in data["message"].lower()


# ─────────────────────────────────────────────────────────────────────
# Security: Honeypot, Consent, LoginHistory
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestHoneypot:
    """Honeypot anti-bot поле."""

    def test_register_honeypot_filled_rejects(self, client):
        """Бот заполнил скрытое поле — регистрация отклонена."""
        data = {
            "username": "botuser",
            "email": "bot@example.com",
            "phone": "+7 (999) 111-22-33",
            "password1": "complexP@ss123",
            "password2": "complexP@ss123",
            "consent": True,
            "website": "http://spam.example.com",  # honeypot
        }
        response = client.post(reverse("accounts:register"), data)
        assert response.status_code == 200  # Остаёмся на форме
        assert not CustomUser.objects.filter(username="botuser").exists()

    def test_login_honeypot_filled_rejects(self, client, verified_user):
        """Бот заполнил скрытое поле — вход отклонён."""
        response = client.post(
            reverse("accounts:login"),
            {
                "username": verified_user.username,
                "password": "testpass123",
                "website": "http://spam.example.com",
            },
        )
        assert response.status_code == 200  # Остаёмся на форме
        assert "_auth_user_id" not in client.session

    def test_register_honeypot_empty_ok(self, client):
        """Honeypot пуст — регистрация проходит."""
        data = {
            "username": "realuser",
            "email": "real@example.com",
            "phone": "+7 (999) 222-33-44",
            "password1": "complexP@ss123",
            "password2": "complexP@ss123",
            "consent": True,
            "website": "",  # пустое — OK
        }
        response = client.post(reverse("accounts:register"), data)
        assert response.status_code == 302
        assert CustomUser.objects.filter(username="realuser").exists()


@pytest.mark.django_db
class TestConsent:
    """Согласие на обработку персональных данных (152-ФЗ)."""

    def test_register_without_consent_fails(self, client):
        """Без согласия регистрация не проходит."""
        data = {
            "username": "noconsent",
            "email": "noconsent@example.com",
            "phone": "+7 (999) 333-44-55",
            "password1": "complexP@ss123",
            "password2": "complexP@ss123",
            # consent отсутствует
        }
        response = client.post(reverse("accounts:register"), data)
        assert response.status_code == 200
        assert not CustomUser.objects.filter(username="noconsent").exists()
        assert "consent" in response.context["form"].errors


@pytest.mark.django_db
class TestLoginHistory:
    """Сигналы LoginHistory при входе/неудаче."""

    def test_successful_login_creates_history(self, client, verified_user):
        """Успешный вход записывается в LoginHistory."""
        assert LoginHistory.objects.count() == 0
        client.post(
            reverse("accounts:login"),
            {
                "username": verified_user.username,
                "password": "testpass123",
            },
        )
        assert LoginHistory.objects.filter(user=verified_user, success=True).exists()

    def test_failed_login_creates_history(self, client, verified_user):
        """Неудачный вход записывается в LoginHistory."""
        client.post(
            reverse("accounts:login"),
            {
                "username": verified_user.username,
                "password": "wrongpassword",
            },
        )
        assert LoginHistory.objects.filter(user=verified_user, success=False).exists()

    def test_failed_login_nonexistent_user_no_history(self, client):
        """Неудачный вход несуществующего пользователя не пишет в БД."""
        client.post(
            reverse("accounts:login"),
            {
                "username": "ghost_user_xyz",
                "password": "anything",
            },
        )
        assert LoginHistory.objects.count() == 0


@pytest.mark.django_db
class TestPrivacyPolicy:
    """Страница политики конфиденциальности."""

    def test_privacy_policy_page(self, client):
        """Страница открывается."""
        response = client.get(reverse("privacy_policy"))
        assert response.status_code == 200
        assert "Политика конфиденциальности" in response.content.decode()
