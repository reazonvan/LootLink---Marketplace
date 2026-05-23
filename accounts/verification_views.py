"""
Views для верификации пользователей (Email и SMS).
"""

import logging
import random

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from core.integrations.sms_service import send_sms

from .forms import ResendVerificationForm, SMSVerificationForm
from .models import CustomUser, EmailVerification

logger = logging.getLogger(__name__)


# verify_email перенесён в accounts.views — здесь оставляем заглушку для совместимости
# импортов в тестах.
from .views import verify_email  # noqa: F401


@login_required
def resend_verification_email(request):
    """
    Повторная отправка письма верификации.
    """
    try:
        verification = EmailVerification.objects.get(user=request.user)

        if verification.is_verified:
            messages.info(request, "Ваш email уже верифицирован.")
            return redirect("accounts:profile", username=request.user.username)

        # Создаем новый токен
        verification.token = EmailVerification.generate_token()
        verification.save()

        # Отправляем письмо
        verification_url = request.build_absolute_uri(
            reverse("accounts:verify_email", kwargs={"token": verification.token})
        )

        from core.email_utils import send_verification_email

        send_verification_email(request.user, verification_url)

        messages.success(request, "Письмо верификации отправлено на ваш email.")
        return redirect("accounts:verification_status")

    except EmailVerification.DoesNotExist:
        # Создаем новую верификацию
        verification = EmailVerification.create_for_user(request.user)

        verification_url = request.build_absolute_uri(
            reverse("accounts:verify_email", kwargs={"token": verification.token})
        )

        from core.email_utils import send_verification_email

        send_verification_email(request.user, verification_url)

        messages.success(request, "Письмо верификации отправлено на ваш email.")
        return redirect("accounts:verification_status")


@login_required
def verification_status(request):
    """
    Статус верификации пользователя.
    """
    try:
        email_verification = EmailVerification.objects.get(user=request.user)
    except EmailVerification.DoesNotExist:
        email_verification = None

    # SMS верификация
    phone_verified = request.user.profile.phone and request.user.profile.is_verified

    context = {
        "email_verification": email_verification,
        "phone_verified": phone_verified,
    }
    return render(request, "accounts/verification_status.html", context)


@login_required
def phone_verification_request(request):
    """
    Запрос SMS кода для верификации телефона.
    """
    from .models import PhoneVerification

    profile = request.user.profile

    if not profile.phone:
        messages.error(request, "Сначала добавьте номер телефона в настройках профиля.")
        return redirect("accounts:profile_edit")

    if profile.is_verified:
        messages.info(request, "Ваш телефон уже верифицирован.")
        return redirect("accounts:verification_status")

    if request.method == "POST":
        # Rate-limit: не более 3 запросов SMS-кода за час на пользователя
        from core.decorators import check_rate_limit

        allowed, _ = check_rate_limit(
            f"sms_request:{request.user.id}", max_attempts=3, window_seconds=3600
        )
        if not allowed:
            messages.error(
                request,
                "Слишком много запросов SMS. Попробуйте через час.",
            )
            return redirect("accounts:phone_verification_confirm")

        verification = PhoneVerification.create_for_user(request.user, profile.phone)
        from core.integrations.sms_service import send_verification_sms

        success = send_verification_sms(profile.phone, verification.code)

        if success:
            messages.success(
                request, f"SMS код отправлен на номер {profile.phone}. Код действителен 10 минут."
            )
            return redirect("accounts:phone_verification_confirm")
        else:
            messages.error(request, "Ошибка отправки SMS. Попробуйте позже.")
            verification.delete()

    return render(request, "accounts/phone_verification_request.html")


@login_required
def phone_verification_confirm(request):
    """
    Подтверждение телефона по SMS коду.
    """
    from .models import PhoneVerification

    profile = request.user.profile

    # Повторная отправка SMS — с защитой от спама
    if request.method == "POST" and "resend" in request.POST:
        if profile.phone:
            from core.decorators import check_rate_limit
            from core.integrations.sms_service import send_verification_sms

            allowed, _ = check_rate_limit(
                f"sms_request:{request.user.id}", max_attempts=3, window_seconds=3600
            )
            if not allowed:
                messages.error(
                    request,
                    "Слишком много запросов SMS. Попробуйте через час.",
                )
                return redirect("accounts:phone_verification_confirm")

            verification = PhoneVerification.create_for_user(request.user, profile.phone)
            success = send_verification_sms(profile.phone, verification.code)
            if success:
                messages.success(request, "Новый код отправлен на ваш номер.")
            else:
                messages.error(request, "Ошибка отправки SMS. Попробуйте позже.")
        return redirect("accounts:phone_verification_confirm")

    if request.method == "POST":
        form = SMSVerificationForm(request.POST)
        if form.is_valid():
            entered_code = form.cleaned_data["code"]

            try:
                verification = PhoneVerification.objects.filter(
                    user=request.user, is_verified=False
                ).latest("created_at")

                success, message = verification.verify(entered_code)

                if success:
                    messages.success(request, "Телефон подтверждён! Добро пожаловать в LootLink!")
                    return redirect("listings:home")
                else:
                    messages.error(request, message)

            except PhoneVerification.DoesNotExist:
                messages.error(request, "Код верификации не найден. Запросите новый код.")
                return redirect("accounts:phone_verification_request")
    else:
        form = SMSVerificationForm()

    context = {
        "form": form,
        "phone": profile.phone,
    }
    return render(request, "accounts/phone_verification_confirm.html", context)


@login_required
@require_http_methods(["POST"])
def request_document_verification(request):
    """Запрос документальной верификации.

    Был заглушкой ("ожидайте проверки", но ничего не происходило). Теперь —
    редиректит на страницу загрузки документов, чтобы пользователь не получал
    ложное сообщение об успешной отправке.
    """
    profile = request.user.profile

    if profile.is_verified:
        return JsonResponse({"success": False, "error": "Уже верифицирован"})

    return JsonResponse(
        {
            "success": True,
            "redirect_url": "/accounts/verification/document/upload/",
            "message": "Загрузите документы для верификации.",
        }
    )


@login_required
def document_verification_upload(request):
    """Загрузка документов для верификации.

    Лимит: 10 документов за 24 часа на пользователя (защита от DoS storage).
    """
    from core.decorators import check_rate_limit

    from .forms import DocumentVerificationForm
    from .models import DocumentVerification

    if request.user.profile.is_verified:
        messages.info(request, "Вы уже верифицированы.")
        return redirect("accounts:verification_status")

    if request.method == "POST":
        allowed, _ = check_rate_limit(
            f"kyc_upload:{request.user.id}", max_attempts=10, window_seconds=86400
        )
        if not allowed:
            messages.error(
                request,
                "Слишком много загрузок документов за сутки. Попробуйте позже.",
            )
            return redirect("accounts:document_verification_upload")

        form = DocumentVerificationForm(request.POST, request.FILES)
        if form.is_valid():
            document = form.save(commit=False)
            document.user = request.user
            document.save()

            messages.success(
                request,
                f'Документ "{document.get_document_type_display()}" загружен. Ожидайте проверки.',
            )
            return redirect("accounts:document_verification_upload")
    else:
        form = DocumentVerificationForm()

    documents = DocumentVerification.objects.filter(user=request.user).order_by("-created_at")
    context = {"form": form, "documents": documents}
    return render(request, "accounts/document_verification_upload.html", context)


@login_required
def document_verification_status(request):
    """
    Статус проверки документов.
    """
    from .models import DocumentVerification

    documents = DocumentVerification.objects.filter(user=request.user).order_by("-created_at")

    context = {
        "documents": documents,
    }
    return render(request, "accounts/document_verification_status.html", context)


@login_required
def serve_kyc_document(request, document_id):
    """Защищённая раздача KYC-документа.

    Доступ только владельцу документа или staff/moderator. Файл
    стримится напрямую из приватного storage — никаких прямых URL.
    """
    from django.http import FileResponse, Http404, HttpResponseForbidden

    from .models import DocumentVerification

    try:
        doc = DocumentVerification.objects.get(pk=document_id)
    except DocumentVerification.DoesNotExist:
        raise Http404

    is_owner = doc.user_id == request.user.id
    is_moderator = request.user.is_staff or (
        hasattr(request.user, "profile") and request.user.profile.is_moderator
    )
    if not (is_owner or is_moderator):
        return HttpResponseForbidden("Нет доступа к этому документу")

    if not doc.document_file:
        raise Http404

    try:
        file_handle = doc.document_file.open("rb")
    except FileNotFoundError:
        raise Http404

    response = FileResponse(file_handle, as_attachment=False)
    # Запрещаем кеширование, чтобы prozy/CDN не раздавали PII.
    response["Cache-Control"] = "private, no-store, max-age=0"
    response["X-Content-Type-Options"] = "nosniff"
    return response
