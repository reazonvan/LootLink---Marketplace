from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.db.models import Avg
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from django_otp.plugins.otp_totp.models import TOTPDevice

from transactions.models import Review

from .forms import (
    ChangePasswordForm,
    CustomAuthenticationForm,
    CustomUserCreationForm,
    PasswordResetConfirmForm,
    PasswordResetRequestForm,
    ProfileUpdateForm,
)
from .models import CustomUser, PasswordResetCode, Profile
from .models_security import LoginHistory


def _get_client_ip(request):
    from core.utils import get_client_ip

    return get_client_ip(request)


def register(request):
    """Регистрация нового пользователя.

    P0-16: после регистрации пользователь логинится, но profile.is_verified=False
    блокирует доступ к чувствительным операциям (createlisting, escrow, withdrawal).
    Полный доступ — только после подтверждения телефона.
    """
    if request.user.is_authenticated:
        return redirect("listings:home")

    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user, backend="accounts.backends.CaseInsensitiveModelBackend")

            # Сохраняем session-маркер для UI — показать "верифицируй телефон" баннер
            request.session["needs_phone_verification"] = True

            messages.success(
                request,
                "Регистрация прошла успешно! Подтвердите номер телефона кодом из SMS, "
                "чтобы открыть все возможности платформы.",
            )
            return redirect("accounts:phone_verification_confirm")
    else:
        form = CustomUserCreationForm()

    return render(request, "accounts/register.html", {"form": form})


def user_login(request):
    """Вход пользователя в систему."""
    if request.user.is_authenticated:
        return redirect("listings:home")

    # Единая статистика платформы для консистентности с главной страницей.
    from core.utils import get_platform_stats

    platform_stats = get_platform_stats()
    total_users = platform_stats["active_users"]
    total_deals = platform_stats["total_deals"]

    if request.method == "POST":
        try:
            form = CustomAuthenticationForm(request, data=request.POST)
            if form.is_valid():
                username = form.cleaned_data.get("username")
                password = form.cleaned_data.get("password")
                user = authenticate(username=username, password=password)
                if user is not None:
                    # Проверяем, включена ли 2FA у пользователя
                    has_2fa = TOTPDevice.objects.filter(user=user, confirmed=True).exists()
                    if has_2fa:
                        # Не логиним — сохраняем user_id в сессию для 2FA
                        request.session["_2fa_user_id"] = user.pk
                        request.session["_2fa_backend"] = user.backend
                        next_page = request.POST.get("next") or request.GET.get("next") or ""
                        request.session["_2fa_next"] = next_page
                        return redirect("accounts:login_2fa")
                    login(request, user)
                    messages.success(request, f"Добро пожаловать, {username}!")
                    # Безопасное перенаправление только на внутренние URL
                    next_page = request.POST.get("next") or request.GET.get("next")
                    if next_page and url_has_allowed_host_and_scheme(
                        url=next_page,
                        allowed_hosts={request.get_host()},
                        require_https=request.is_secure(),
                    ):
                        return redirect(next_page)
                    return redirect("listings:home")
                else:
                    messages.error(request, "Неверное имя пользователя или пароль.")
            else:
                # Если форма невалидна, показываем ошибки
                messages.error(request, "Неверное имя пользователя или пароль.")
        except Exception as e:
            # Логируем ошибку и показываем пользователю понятное сообщение
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"Ошибка при входе: {e}")
            messages.error(request, "Произошла ошибка при входе. Попробуйте еще раз.")
            form = CustomAuthenticationForm()
    else:
        form = CustomAuthenticationForm()

    from listings.models import Game

    total_games = Game.objects.filter(is_active=True).count()

    context = {
        "form": form,
        "total_users": total_users,
        "total_deals": total_deals,
        "total_games": total_games,
    }
    return render(request, "accounts/login.html", context)


def login_2fa_verify(request):
    """Проверка TOTP-кода при входе (2FA).

    Rate-limit: 5 попыток / 5 минут на user_id (защита от брутфорса TOTP).
    После исчерпания лимита — сброс _2fa_user_id из сессии и принудительный
    повторный вход.
    """
    user_id = request.session.get("_2fa_user_id")
    backend = request.session.get("_2fa_backend")
    if not user_id:
        return redirect("accounts:login")

    if request.method == "POST":
        from core.decorators import check_rate_limit
        from core.models_audit import SecurityAuditLog

        token = request.POST.get("token", "").strip()
        try:
            user = CustomUser.objects.get(pk=user_id)
        except CustomUser.DoesNotExist:
            request.session.pop("_2fa_user_id", None)
            return redirect("accounts:login")

        # Атомарный rate-limit: 5 попыток за 5 минут на пользователя
        rl_key = f"2fa_attempts:{user_id}"
        allowed, current = check_rate_limit(rl_key, max_attempts=5, window_seconds=300)
        if not allowed:
            SecurityAuditLog.log(
                action_type="rate_limit_exceeded",
                user=user,
                description="Превышен лимит попыток ввода 2FA — возможный брутфорс",
                risk_level="high",
                request=request,
                metadata={"attempts": current},
            )
            request.session.pop("_2fa_user_id", None)
            request.session.pop("_2fa_backend", None)
            request.session.pop("_2fa_next", None)
            messages.error(
                request,
                "Слишком много попыток. Войдите заново через 5 минут.",
            )
            return redirect("accounts:login")

        device = TOTPDevice.objects.filter(user=user, confirmed=True).first()
        if device and device.verify_token(token):
            user.backend = backend
            login(request, user)
            next_page = request.session.pop("_2fa_next", "")
            request.session.pop("_2fa_user_id", None)
            request.session.pop("_2fa_backend", None)
            # Сбрасываем счётчик попыток после успеха
            from django.core.cache import cache

            cache.delete(rl_key)
            messages.success(request, f"Добро пожаловать, {user.username}!")
            if next_page and url_has_allowed_host_and_scheme(
                url=next_page,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure(),
            ):
                return redirect(next_page)
            return redirect("listings:home")
        else:
            SecurityAuditLog.log(
                action_type="login_failed",
                user=user,
                description="Неверный 2FA-код",
                risk_level="medium",
                request=request,
            )
            messages.error(request, "Неверный код. Попробуйте ещё раз.")

    return render(request, "accounts/login_2fa.html")


@login_required
@require_POST
def user_logout(request):
    """Выход пользователя из системы."""
    logout(request)
    messages.info(request, "Вы вышли из системы.")
    return redirect("listings:home")


def profile(request, username):
    """Просмотр профиля пользователя с оптимизацией запросов."""
    from django.core.paginator import Paginator

    # Case-insensitive поиск (argear = Argear)
    user = get_object_or_404(CustomUser, username__iexact=username)

    # Исправление: проверка на существование profile (уже реализовано)
    # Используем get_or_create для атомарности
    try:
        profile, created = Profile.objects.get_or_create(user=user)
        if created:
            messages.info(request, "Профиль был создан автоматически.")
    except Exception as e:
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"Ошибка при создании профиля для {username}: {e}")
        messages.error(request, "Произошла ошибка при загрузке профиля.")
        return redirect("listings:home")

    # Получаем отзывы о пользователе с оптимизацией
    reviews = (
        Review.objects.filter(reviewed_user=user)
        .select_related(
            "reviewer", "reviewer__profile", "purchase_request", "purchase_request__listing"
        )
        .order_by("-created_at")
    )

    # Добавляем пагинацию для отзывов
    paginator = Paginator(reviews, 10)  # 10 отзывов на страницу
    page_number = request.GET.get("page")
    reviews_page = paginator.get_page(page_number)

    # Статистика
    is_own_profile = request.user == user

    context = {
        "profile_user": user,
        "profile": profile,
        "reviews": reviews_page,
        "is_own_profile": is_own_profile,
    }

    return render(request, "accounts/profile.html", context)


@login_required
def profile_edit(request):
    """
    Редактирование профиля.

    ВАЖНО: Username, Email и Phone нельзя изменить.
    Редактируется только дополнительная информация профиля.
    """
    # Проверяем наличие профиля
    profile, created = Profile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        profile_form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user.profile)

        if profile_form.is_valid():
            profile_form.save()
            messages.success(request, "Профиль успешно обновлен!")
            return redirect("accounts:profile", username=request.user.username)
    else:
        profile_form = ProfileUpdateForm(instance=request.user.profile)

    context = {
        "profile_form": profile_form,
    }

    return render(request, "accounts/profile_edit.html", context)


@login_required
def my_listings(request):
    """Мои объявления с оптимизацией запросов."""
    from django.core.paginator import Paginator

    from listings.models import Listing

    # Оптимизация: используем select_related для избежания N+1 запросов
    listings = (
        Listing.objects.filter(seller=request.user).select_related("game").order_by("-created_at")
    )

    # Пагинация
    paginator = Paginator(listings, 20)  # 20 объявлений на страницу
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
    }

    return render(request, "accounts/my_listings.html", context)


@login_required
def my_purchases(request):
    """Мои покупки с оптимизацией запросов."""
    from django.core.paginator import Paginator

    from transactions.models import PurchaseRequest

    # Оптимизация: добавляем game для listing
    purchases = (
        PurchaseRequest.objects.filter(buyer=request.user)
        .select_related("listing", "listing__game", "seller", "seller__profile")
        .order_by("-created_at")
    )

    # Пагинация
    paginator = Paginator(purchases, 20)  # 20 покупок на страницу
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
    }

    return render(request, "accounts/my_purchases.html", context)


@login_required
def my_sales(request):
    """Мои продажи с оптимизацией запросов."""
    from django.core.paginator import Paginator

    from transactions.models import PurchaseRequest

    # Оптимизация: добавляем game для listing и profile для buyer
    sales = (
        PurchaseRequest.objects.filter(seller=request.user)
        .select_related("listing", "listing__game", "buyer", "buyer__profile")
        .order_by("-created_at")
    )

    # Пагинация
    paginator = Paginator(sales, 20)  # 20 продаж на страницу
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
    }

    return render(request, "accounts/my_sales.html", context)


def password_reset_request(request):
    """Запрос на сброс пароля - отправка кода на email и SMS."""
    if request.method == "POST":
        # Rate limiting: 3 запроса за 10 минут на IP
        from django.core.cache import cache

        ip = _get_client_ip(request)
        cache_key = f"password_reset_rate_{ip}"
        attempts = cache.get(cache_key, 0)
        if attempts >= 3:
            messages.error(request, "Слишком много запросов. Подождите 10 минут.")
            return render(
                request,
                "accounts/password_reset_request.html",
                {"form": PasswordResetRequestForm()},
            )
        cache.set(cache_key, attempts + 1, 600)

        form = PasswordResetRequestForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]

            from core.integrations.email_service import EmailService

            try:
                user = CustomUser.objects.get(email=email)
            except CustomUser.DoesNotExist:
                # Не раскрываем существование аккаунта — отправляем info-письмо
                try:
                    EmailService.send_no_account_email(email)
                except Exception:
                    pass
                messages.success(
                    request,
                    "Если аккаунт с таким email существует, код будет отправлен.",
                )
                request.session["reset_email"] = email
                return redirect("accounts:password_reset_confirm")

            # Создаём код сброса
            reset_code = PasswordResetCode.create_code(user)

            email_sent = False
            sms_sent = False

            # Отправляем email через EmailService
            try:
                email_sent = EmailService.send_password_reset_email(user, reset_code.code)
            except Exception as e:
                import logging

                logger = logging.getLogger(__name__)
                logger.error(f"Ошибка отправки email: {e}")

            # Отправляем СМС если у пользователя указан телефон
            if user.profile.phone:
                try:
                    from core.integrations.sms_service import send_password_reset_sms

                    sms_sent = send_password_reset_sms(
                        user.profile.phone, reset_code.code, user.username
                    )
                except Exception as e:
                    import logging

                    logger = logging.getLogger(__name__)
                    logger.error(f"Ошибка отправки СМС: {e}")

            messages.success(
                request,
                "Если аккаунт с таким email существует, код будет отправлен.",
            )

            request.session["reset_email"] = email
            return redirect("accounts:password_reset_confirm")
    else:
        form = PasswordResetRequestForm()

    context = {
        "form": form,
    }

    return render(request, "accounts/password_reset_request.html", context)


def verify_email(request, token):
    """Верификация email адреса по токену."""
    from datetime import timedelta

    from django.utils import timezone

    from .models import EmailVerification

    try:
        verification = EmailVerification.objects.get(token=token)

        # Проверяем что токен не старше 24 часов
        if verification.created_at < timezone.now() - timedelta(hours=24):
            messages.error(request, "Ссылка верификации истекла. Запросите новую.")
            return redirect("accounts:login")

        # Проверяем что еще не верифицирован
        if verification.is_verified:
            messages.info(request, "Email уже подтвержден.")
            return redirect("accounts:login")

        # Верифицируем
        verification.verify()

        messages.success(request, "Email успешно подтвержден! Теперь вы можете войти.")
        return redirect("accounts:login")

    except EmailVerification.DoesNotExist:
        messages.error(request, "Неверная ссылка верификации.")
        return redirect("accounts:login")


def resend_verification_email(request):
    """Повторная отправка письма верификации.

    P3 rate-limit: не более 5 запросов за час, чтобы не дать спамить SMTP.
    """
    if not request.user.is_authenticated:
        messages.error(request, "Войдите в систему для повторной отправки письма.")
        return redirect("accounts:login")

    from django.urls import reverse

    from core.decorators import check_rate_limit

    from .models import EmailVerification

    allowed, _ = check_rate_limit(
        f"email_resend:{request.user.id}", max_attempts=5, window_seconds=3600
    )
    if not allowed:
        messages.error(
            request, "Слишком много запросов на повторную отправку. Попробуйте через час."
        )
        return redirect("accounts:profile", username=request.user.username)

    try:
        verification = request.user.email_verification
        if verification.is_verified:
            messages.info(request, "Ваш email уже подтвержден.")
            return redirect("accounts:profile", username=request.user.username)
    except EmailVerification.DoesNotExist:
        verification = EmailVerification.create_for_user(request.user)

    # P3: используем request.build_absolute_uri вместо ручной сборки URL.
    verification_url = request.build_absolute_uri(
        reverse("accounts:verify_email", kwargs={"token": verification.token})
    )

    subject = "Подтвердите ваш email - LootLink"
    message = f"""
Здравствуйте, {request.user.username}!

Перейдите по ссылке для подтверждения email:

{verification_url}

Ссылка действительна в течение 24 часов.

С уважением,
Команда LootLink
"""

    try:
        # Phase 13: ставим письмо в Celery — синхронный send_mail()
        # блокировал ответ и мог упасть при медленном SMTP.
        from django.db import transaction as db_transaction

        from core.tasks import send_email_async

        recipient = request.user.email
        db_transaction.on_commit(lambda: send_email_async.delay(subject, message, recipient))
        messages.success(request, f"Письмо с подтверждением отправлено на {request.user.email}")
    except Exception as e:
        messages.error(request, f"Ошибка отправки письма: {e}")

    return redirect("accounts:profile", username=request.user.username)


def password_reset_confirm(request):
    """Подтверждение сброса пароля с вводом кода."""
    email = request.session.get("reset_email")
    if not email:
        messages.error(request, "Сессия истекла. Запросите код заново.")
        return redirect("accounts:password_reset_request")

    try:
        user = CustomUser.objects.get(email=email)
    except CustomUser.DoesNotExist:
        messages.error(request, "Пользователь не найден.")
        return redirect("accounts:password_reset_request")

    if request.method == "POST":
        form = PasswordResetConfirmForm(request.POST, user=user)
        if form.is_valid():
            form.save()
            del request.session["reset_email"]
            messages.success(request, "Пароль успешно изменён! Войдите с новым паролем.")
            return redirect("accounts:login")
    else:
        form = PasswordResetConfirmForm(user=user)

    context = {
        "form": form,
        "email": email,
    }

    return render(request, "accounts/password_reset_confirm.html", context)


def check_username_available(request):
    """AJAX endpoint для проверки доступности никнейма.

    P0-18: жёсткий rate-limit + общий дневной лимит, чтобы не дать
    перебрать базу пользователей за пару часов. Атомарный incr.
    """
    from django.http import JsonResponse

    from core.decorators import check_rate_limit

    ip = _get_client_ip(request)
    # 10 запросов в минуту + 500 в сутки на IP
    allowed, _ = check_rate_limit(f"username_check_rate_min_{ip}", 10, 60)
    if not allowed:
        return JsonResponse(
            {"available": False, "message": "Слишком много запросов. Подождите минуту."},
            status=429,
        )
    allowed, _ = check_rate_limit(f"username_check_rate_day_{ip}", 500, 86400)
    if not allowed:
        return JsonResponse(
            {"available": False, "message": "Дневной лимит исчерпан."},
            status=429,
        )

    username = request.GET.get("username", "").strip()

    if not username:
        return JsonResponse({"available": False, "message": "Введите имя пользователя"})

    if len(username) < 3:
        return JsonResponse({"available": False, "message": "Минимум 3 символа"})

    if len(username) > 150:
        return JsonResponse({"available": False, "message": "Максимум 150 символов"})

    # Проверяем что username содержит только допустимые символы
    import re

    if not re.match(r"^[\w.@+-]+$", username):
        return JsonResponse(
            {
                "available": False,
                "message": "Недопустимые символы. Разрешены: буквы, цифры, @/./+/-/_",
            }
        )

    # Case-insensitive проверка (argear = Argear)
    exists = CustomUser.objects.filter(username__iexact=username).exists()

    if exists:
        return JsonResponse({"available": False, "message": "Этот никнейм уже занят"})

    return JsonResponse({"available": True, "message": "Никнейм доступен"})


def check_email_available(request):
    """AJAX endpoint для проверки доступности email.

    P0-18: жёсткий rate-limit + дневной лимит.
    """
    from django.http import JsonResponse

    from core.decorators import check_rate_limit

    ip = _get_client_ip(request)
    allowed, _ = check_rate_limit(f"email_check_rate_min_{ip}", 10, 60)
    if not allowed:
        return JsonResponse(
            {"available": False, "message": "Слишком много запросов. Подождите минуту."},
            status=429,
        )
    allowed, _ = check_rate_limit(f"email_check_rate_day_{ip}", 500, 86400)
    if not allowed:
        return JsonResponse(
            {"available": False, "message": "Дневной лимит исчерпан."},
            status=429,
        )

    email = request.GET.get("email", "").strip()

    if not email:
        return JsonResponse({"available": False, "message": "Введите email"})

    # Простая валидация email
    import re

    email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if not re.match(email_pattern, email):
        return JsonResponse({"available": False, "message": "Некорректный формат email"})

    exists = CustomUser.objects.filter(email__iexact=email).exists()

    if exists:
        return JsonResponse({"available": False, "message": "Этот email уже зарегистрирован"})

    return JsonResponse({"available": True, "message": "Email доступен"})


def check_phone_available(request):
    """AJAX endpoint для проверки доступности телефона.

    P0-18: жёсткий rate-limit + проверка нормализованного номера, чтобы
    исключить дубли в разных форматах.
    """
    from django.http import JsonResponse

    from core.decorators import check_rate_limit
    from core.utils import clean_phone_number

    ip = _get_client_ip(request)
    allowed, _ = check_rate_limit(f"phone_check_rate_min_{ip}", 10, 60)
    if not allowed:
        return JsonResponse(
            {"available": False, "message": "Слишком много запросов. Подождите минуту."},
            status=429,
        )
    allowed, _ = check_rate_limit(f"phone_check_rate_day_{ip}", 500, 86400)
    if not allowed:
        return JsonResponse(
            {"available": False, "message": "Дневной лимит исчерпан."},
            status=429,
        )

    phone = request.GET.get("phone", "").strip()

    if not phone:
        return JsonResponse({"available": False, "message": "Введите номер телефона"})

    import re

    phone_digits = re.sub(r"\D", "", phone)
    if len(phone_digits) < 10 or len(phone_digits) > 11:
        return JsonResponse({"available": False, "message": "Некорректный номер телефона"})

    # Сравниваем по нормализованному виду
    normalized = clean_phone_number(phone)
    if Profile.objects.filter(phone=normalized).exists():
        return JsonResponse({"available": False, "message": "Этот номер уже зарегистрирован"})

    return JsonResponse({"available": True, "message": "Номер доступен"})


# ═══════════════════════════════════════════════════════════════
# НАСТРОЙКИ АККАУНТА
# ═══════════════════════════════════════════════════════════════


@login_required
def account_settings(request):
    """Страница настроек аккаунта — данные, безопасность, сессии."""
    from django.contrib.sessions.models import Session
    from django.utils import timezone

    from django_otp.plugins.otp_totp.models import TOTPDevice

    user = request.user
    profile, _ = Profile.objects.get_or_create(user=user)

    # 2FA статус
    has_2fa = TOTPDevice.objects.filter(user=user, confirmed=True).exists()

    # Смена пароля
    password_form = ChangePasswordForm(user=user)
    password_changed = False

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "change_password":
            password_form = ChangePasswordForm(request.POST, user=user)
            if password_form.is_valid():
                password_form.save()
                from django.contrib.auth import update_session_auth_hash

                update_session_auth_hash(request, user)
                messages.success(request, "Пароль успешно изменён.")
                password_changed = True
                password_form = ChangePasswordForm(user=user)

    # Активные сессии
    current_session_key = request.session.session_key
    sessions = Session.objects.filter(expire_date__gte=timezone.now())
    user_sessions = []
    for session in sessions:
        data = session.get_decoded()
        if str(data.get("_auth_user_id")) == str(user.pk):
            user_sessions.append(
                {
                    "session_key": session.session_key,
                    "expire_date": session.expire_date,
                    "is_current": session.session_key == current_session_key,
                }
            )

    # Последние входы (с устройствами)
    recent_logins = LoginHistory.objects.filter(user=user, success=True).order_by("-created_at")[
        :20
    ]

    context = {
        "profile": profile,
        "has_2fa": has_2fa,
        "password_form": password_form,
        "password_changed": password_changed,
        "user_sessions": user_sessions,
        "recent_logins": recent_logins,
        "active_tab": request.GET.get("tab", "account"),
    }
    return render(request, "accounts/settings.html", context)


@login_required
@require_POST
def terminate_session(request):
    """Завершить конкретную сессию."""
    from django.contrib.sessions.models import Session

    session_key = request.POST.get("session_key")
    if session_key == request.session.session_key:
        messages.error(request, "Нельзя завершить текущую сессию.")
        return redirect("accounts:account_settings")
    try:
        session = Session.objects.get(session_key=session_key)
        data = session.get_decoded()
        if str(data.get("_auth_user_id")) == str(request.user.pk):
            session.delete()
            messages.success(request, "Сессия завершена.")
        else:
            messages.error(request, "Нет доступа к этой сессии.")
    except Session.DoesNotExist:
        messages.error(request, "Сессия не найдена.")
    return redirect("accounts:account_settings")


@login_required
@require_POST
def terminate_all_sessions(request):
    """Завершить все сессии кроме текущей."""
    from django.contrib.sessions.models import Session
    from django.utils import timezone

    current_key = request.session.session_key
    sessions = Session.objects.filter(expire_date__gte=timezone.now())
    count = 0
    for session in sessions:
        if session.session_key == current_key:
            continue
        data = session.get_decoded()
        if str(data.get("_auth_user_id")) == str(request.user.pk):
            session.delete()
            count += 1
    messages.success(request, f"Завершено сессий: {count}")
    return redirect("accounts:account_settings")
