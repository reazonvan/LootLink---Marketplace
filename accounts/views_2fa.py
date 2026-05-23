"""
Views для двухфакторной аутентификации (2FA).
Использует django-otp.
"""

import base64
import io

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render

import qrcode
from django_otp.plugins.otp_totp.models import TOTPDevice
from django_otp.util import random_hex

from core.models_audit import SecurityAuditLog


@login_required
def setup_2fa(request):
    """
    Настройка двухфакторной аутентификации.
    Генерирует QR код для Google Authenticator / Authy.
    """
    user = request.user

    # Проверяем есть ли уже 2FA
    device = TOTPDevice.objects.filter(user=user, confirmed=True).first()

    if device:
        # 2FA уже настроена
        context = {"2fa_enabled": True, "device": device}
        return render(request, "accounts/2fa/setup.html", context)

    # Создаем новое устройство (если еще нет)
    unconfirmed_device = TOTPDevice.objects.filter(user=user, confirmed=False).first()

    if not unconfirmed_device:
        unconfirmed_device = TOTPDevice.objects.create(
            user=user, name=f"{user.username}-totp", confirmed=False
        )

    # Генерируем QR код
    otpauth_url = unconfirmed_device.config_url

    # Создаем QR код
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(otpauth_url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    # Конвертируем в base64 для отображения
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    img_str = base64.b64encode(buffer.getvalue()).decode()

    # django-otp хранит ключ в hex, а TOTP-приложения ожидают base32
    secret_base32 = base64.b32encode(bytes.fromhex(unconfirmed_device.key)).decode()

    context = {
        "2fa_enabled": False,
        "qr_code": img_str,
        "secret_key": secret_base32,
        "device_id": unconfirmed_device.id,
    }

    return render(request, "accounts/2fa/setup.html", context)


@login_required
def verify_2fa(request):
    """Подтверждение настройки 2FA с помощью кода.

    Rate-limit: 5 попыток / 5 минут на user — защита от подбора секрета
    через брутфорс кода активации.
    """
    if request.method != "POST":
        return redirect("accounts:setup_2fa")

    from core.decorators import check_rate_limit

    user = request.user
    device_id = request.POST.get("device_id")
    token = request.POST.get("token", "").strip()

    if not token:
        messages.error(request, "Введите код из приложения.")
        return redirect("accounts:setup_2fa")

    rl_key = f"2fa_setup_attempts:{user.id}"
    allowed, _ = check_rate_limit(rl_key, max_attempts=5, window_seconds=300)
    if not allowed:
        SecurityAuditLog.log(
            action_type="rate_limit_exceeded",
            user=user,
            description="Превышен лимит попыток подтверждения 2FA-устройства",
            risk_level="high",
            request=request,
        )
        messages.error(request, "Слишком много попыток. Подождите 5 минут.")
        return redirect("accounts:setup_2fa")

    try:
        device = TOTPDevice.objects.get(id=device_id, user=user, confirmed=False)
    except TOTPDevice.DoesNotExist:
        messages.error(request, "Устройство не найдено.")
        return redirect("accounts:setup_2fa")

    if device.verify_token(token):
        device.confirmed = True
        device.save(update_fields=["confirmed"])

        # Сбрасываем счётчик после успеха
        from django.core.cache import cache

        cache.delete(rl_key)

        SecurityAuditLog.log(
            action_type="2fa_enabled",
            user=user,
            description="Двухфакторная аутентификация включена",
            risk_level="low",
            request=request,
        )
        _notify_security_change(user, action="включена")

        messages.success(request, "Двухфакторная аутентификация успешно настроена!")
        return redirect("accounts:profile", username=user.username)
    else:
        messages.error(request, "Неверный код. Попробуйте еще раз.")
        return redirect("accounts:setup_2fa")


@login_required
def disable_2fa(request):
    """Отключение 2FA с обязательным паролем и уведомлением владельца.

    P0-19: отключение 2FA — критичное действие. Отправляем email-алерт
    на привязанную почту, чтобы владелец узнал о компрометации сразу.
    """
    if request.method != "POST":
        return redirect("accounts:profile", username=request.user.username)

    user = request.user
    password = request.POST.get("password", "")

    if not user.check_password(password):
        SecurityAuditLog.log(
            action_type="login_failed",
            user=user,
            description="Неверный пароль при попытке отключить 2FA",
            risk_level="high",
            request=request,
        )
        messages.error(request, "Неверный пароль.")
        return redirect("accounts:profile", username=user.username)

    deleted_count = TOTPDevice.objects.filter(user=user).delete()[0]

    if deleted_count > 0:
        SecurityAuditLog.log(
            action_type="2fa_disabled",
            user=user,
            description="Двухфакторная аутентификация отключена",
            risk_level="high",
            request=request,
        )
        _notify_security_change(user, action="отключена")

        messages.success(
            request,
            "Двухфакторная аутентификация отключена. На вашу почту отправлено "
            "уведомление — если это были не вы, срочно смените пароль.",
        )
    else:
        messages.info(request, "2FA не была настроена.")

    return redirect("accounts:profile", username=user.username)


def _notify_security_change(user, action: str) -> None:
    """Email-алерт о критическом изменении настроек 2FA."""
    if not user.email:
        return
    try:
        from django.db import transaction as db_transaction

        from core.tasks import send_email_async

        subject = f"Изменение настроек безопасности — LootLink"
        body = (
            f"Здравствуйте, {user.username}!\n\n"
            f"Двухфакторная аутентификация на вашем аккаунте {action}.\n\n"
            f"Если это были не вы — срочно:\n"
            f"  1. Смените пароль\n"
            f"  2. Заверьте сессии в настройках аккаунта\n"
            f"  3. Свяжитесь с поддержкой\n\n"
            f"С уважением,\nКоманда LootLink"
        )
        recipient = user.email
        db_transaction.on_commit(lambda: send_email_async.delay(subject, body, recipient))
    except Exception:
        import logging

        logging.getLogger(__name__).exception("Не удалось отправить 2FA-алерт")


@login_required
def get_2fa_status(request):
    """API endpoint для получения статуса 2FA."""
    user = request.user

    device = TOTPDevice.objects.filter(user=user, confirmed=True).first()

    return JsonResponse(
        {"enabled": device is not None, "device_name": device.name if device else None}
    )
