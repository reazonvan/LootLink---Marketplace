"""
Views для двухфакторной аутентификации (2FA).
Использует django-otp.
"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django_otp.plugins.otp_totp.models import TOTPDevice
from django_otp.util import random_hex
import qrcode
import io
import base64
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
        context = {
            '2fa_enabled': True,
            'device': device
        }
        return render(request, 'accounts/2fa/setup.html', context)
    
    # Создаем новое устройство (если еще нет)
    unconfirmed_device = TOTPDevice.objects.filter(user=user, confirmed=False).first()
    
    if not unconfirmed_device:
        unconfirmed_device = TOTPDevice.objects.create(
            user=user,
            name=f'{user.username}-totp',
            confirmed=False
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
    img.save(buffer, format='PNG')
    buffer.seek(0)
    img_str = base64.b64encode(buffer.getvalue()).decode()
    
    context = {
        '2fa_enabled': False,
        'qr_code': img_str,
        'secret_key': unconfirmed_device.key,
        'device_id': unconfirmed_device.id
    }
    
    return render(request, 'accounts/2fa/setup.html', context)


@login_required
def verify_2fa(request):
    """Подтверждение настройки 2FA с помощью кода."""
    if request.method != 'POST':
        return redirect('accounts:setup_2fa')
    
    user = request.user
    device_id = request.POST.get('device_id')
    token = request.POST.get('token', '').strip()
    
    if not token:
        messages.error(request, 'Введите код из приложения.')
        return redirect('accounts:setup_2fa')
    
    try:
        device = TOTPDevice.objects.get(id=device_id, user=user, confirmed=False)
    except TOTPDevice.DoesNotExist:
        messages.error(request, 'Устройство не найдено.')
        return redirect('accounts:setup_2fa')
    
    # Проверяем токен
    if device.verify_token(token):
        # Подтверждаем устройство
        device.confirmed = True
        device.save()
        
        # Логируем в audit
        SecurityAuditLog.log(
            action_type='2fa_enabled',
            user=user,
            description='Двухфакторная аутентификация включена',
            risk_level='low',
            request=request
        )
        
        messages.success(request, '✅ Двухфакторная аутентификация успешно настроена!')
        return redirect('accounts:profile', username=user.username)
    else:
        messages.error(request, '❌ Неверный код. Попробуйте еще раз.')
        return redirect('accounts:setup_2fa')


@login_required
def disable_2fa(request):
    """Отключение 2FA."""
    if request.method != 'POST':
        return redirect('accounts:profile', username=request.user.username)
    
    user = request.user
    password = request.POST.get('password', '')
    
    # Проверяем пароль для безопасности
    if not user.check_password(password):
        messages.error(request, 'Неверный пароль.')
        return redirect('accounts:profile', username=user.username)
    
    # Удаляем все TOTP устройства
    deleted_count = TOTPDevice.objects.filter(user=user).delete()[0]
    
    if deleted_count > 0:
        # Логируем в audit
        SecurityAuditLog.log(
            action_type='2fa_disabled',
            user=user,
            description='Двухфакторная аутентификация отключена',
            risk_level='medium',
            request=request
        )
        
        messages.success(request, 'Двухфакторная аутентификация отключена.')
    else:
        messages.info(request, '2FA не была настроена.')
    
    return redirect('accounts:profile', username=user.username)


@login_required
def get_2fa_status(request):
    """API endpoint для получения статуса 2FA."""
    user = request.user
    
    device = TOTPDevice.objects.filter(user=user, confirmed=True).first()
    
    return JsonResponse({
        'enabled': device is not None,
        'device_name': device.name if device else None
    })

