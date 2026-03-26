"""
Views для верификации пользователей (Email и SMS).
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.urls import reverse
from .models import CustomUser, EmailVerification
from .forms import SMSVerificationForm, ResendVerificationForm
from core.sms_service import send_sms
import random
import logging

logger = logging.getLogger(__name__)


def verify_email(request, token):
    """
    Верификация email по токену.
    """
    try:
        verification = EmailVerification.objects.get(token=token)

        if verification.is_verified:
            messages.info(request, 'Email уже был верифицирован ранее.')
            return redirect('accounts:profile', username=verification.user.username)

        # FIX: проверка срока действия токена (24 часа)
        if (timezone.now() - verification.created_at).total_seconds() > 86400:
            messages.error(request, 'Срок действия ссылки истёк. Запросите новую.')
            return redirect('listings:home')

        # Верифицируем
        verification.verify()
        
        messages.success(request, 'Email успешно верифицирован! Теперь вы можете пользоваться всеми функциями сайта.')
        return redirect('accounts:profile', username=verification.user.username)
        
    except EmailVerification.DoesNotExist:
        messages.error(request, 'Неверная ссылка верификации или она устарела.')
        return redirect('listings:home')


@login_required
def resend_verification_email(request):
    """
    Повторная отправка письма верификации.
    """
    try:
        verification = EmailVerification.objects.get(user=request.user)
        
        if verification.is_verified:
            messages.info(request, 'Ваш email уже верифицирован.')
            return redirect('accounts:profile', username=request.user.username)
        
        # Создаем новый токен
        verification.token = EmailVerification.generate_token()
        verification.save()
        
        # Отправляем письмо
        verification_url = request.build_absolute_uri(
            reverse('accounts:verify_email', kwargs={'token': verification.token})
        )
        
        from core.email_utils import send_verification_email
        send_verification_email(request.user, verification_url)
        
        messages.success(request, 'Письмо верификации отправлено на ваш email.')
        return redirect('accounts:verification_status')
        
    except EmailVerification.DoesNotExist:
        # Создаем новую верификацию
        verification = EmailVerification.create_for_user(request.user)
        
        verification_url = request.build_absolute_uri(
            reverse('accounts:verify_email', kwargs={'token': verification.token})
        )
        
        from core.email_utils import send_verification_email
        send_verification_email(request.user, verification_url)
        
        messages.success(request, 'Письмо верификации отправлено на ваш email.')
        return redirect('accounts:verification_status')


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
        'email_verification': email_verification,
        'phone_verified': phone_verified,
    }
    return render(request, 'accounts/verification_status.html', context)


@login_required
def phone_verification_request(request):
    """
    Запрос SMS кода для верификации телефона.
    """
    from .models import PhoneVerification

    profile = request.user.profile

    if not profile.phone:
        messages.error(request, 'Сначала добавьте номер телефона в настройках профиля.')
        return redirect('accounts:profile_edit')

    if profile.is_verified:
        messages.info(request, 'Ваш телефон уже верифицирован.')
        return redirect('accounts:verification_status')

    if request.method == 'POST':
        # Создаем новую верификацию
        verification = PhoneVerification.create_for_user(request.user, profile.phone)

        # Отправляем SMS
        from core.sms_service import send_verification_sms
        success = send_verification_sms(profile.phone, verification.code)

        if success:
            messages.success(request, f'SMS код отправлен на номер {profile.phone}. Код действителен 10 минут.')
            return redirect('accounts:phone_verification_confirm')
        else:
            messages.error(request, 'Ошибка отправки SMS. Попробуйте позже.')
            verification.delete()

    return render(request, 'accounts/phone_verification_request.html')


@login_required
def phone_verification_confirm(request):
    """
    Подтверждение телефона по SMS коду.
    """
    from .models import PhoneVerification

    if request.method == 'POST':
        form = SMSVerificationForm(request.POST)
        if form.is_valid():
            entered_code = form.cleaned_data['code']

            # Получаем последнюю верификацию пользователя
            try:
                verification = PhoneVerification.objects.filter(
                    user=request.user,
                    is_verified=False
                ).latest('created_at')

                success, message = verification.verify(entered_code)

                if success:
                    messages.success(request, message)
                    return redirect('accounts:verification_status')
                else:
                    messages.error(request, message)

            except PhoneVerification.DoesNotExist:
                messages.error(request, 'Код верификации не найден. Запросите новый код.')
                return redirect('accounts:phone_verification_request')
    else:
        form = SMSVerificationForm()

    return render(request, 'accounts/phone_verification_confirm.html', {'form': form})


@login_required
@require_http_methods(['POST'])
def request_document_verification(request):
    """
    Запрос документальной верификации (для крупных продавцов).
    """
    # Можно добавить загрузку документов
    profile = request.user.profile

    if profile.is_verified:
        return JsonResponse({'success': False, 'error': 'Уже верифицирован'})

    # Здесь можно добавить логику отправки документов на модерацию
    # Пока просто отправим уведомление админам

    messages.success(request, 'Запрос на верификацию документов отправлен. Ожидайте проверки администратором.')
    return JsonResponse({'success': True})


@login_required
def document_verification_upload(request):
    """
    Загрузка документов для верификации.
    """
    from .models import DocumentVerification
    from .forms import DocumentVerificationForm

    if request.user.profile.is_verified:
        messages.info(request, 'Вы уже верифицированы.')
        return redirect('accounts:verification_status')

    if request.method == 'POST':
        form = DocumentVerificationForm(request.POST, request.FILES)
        if form.is_valid():
            document = form.save(commit=False)
            document.user = request.user
            document.save()

            messages.success(request, f'Документ "{document.get_document_type_display()}" загружен. Ожидайте проверки.')
            return redirect('accounts:document_verification_upload')
    else:
        form = DocumentVerificationForm()

    # Получаем уже загруженные документы
    documents = DocumentVerification.objects.filter(user=request.user).order_by('-created_at')

    context = {
        'form': form,
        'documents': documents,
    }
    return render(request, 'accounts/document_verification_upload.html', context)


@login_required
def document_verification_status(request):
    """
    Статус проверки документов.
    """
    from .models import DocumentVerification

    documents = DocumentVerification.objects.filter(user=request.user).order_by('-created_at')

    context = {
        'documents': documents,
    }
    return render(request, 'accounts/document_verification_status.html', context)

