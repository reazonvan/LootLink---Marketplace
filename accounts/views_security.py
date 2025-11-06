"""
Views для безопасности: 2FA, история входов.
"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django_otp.plugins.otp_totp.models import TOTPDevice
from .models_security import LoginHistory, SuspiciousActivity
import qrcode
import io
import base64


@login_required
def security_settings(request):
    """Настройки безопасности"""
    # 2FA статус
    totp_devices = TOTPDevice.objects.filter(user=request.user, confirmed=True)
    has_2fa = totp_devices.exists()
    
    # История входов
    recent_logins = LoginHistory.objects.filter(
        user=request.user
    ).order_by('-created_at')[:10]
    
    # Подозрительная активность
    suspicious = SuspiciousActivity.objects.filter(
        user=request.user,
        is_resolved=False
    ).order_by('-created_at')[:5]
    
    context = {
        'has_2fa': has_2fa,
        'recent_logins': recent_logins,
        'suspicious_activities': suspicious,
    }
    return render(request, 'accounts/security_settings.html', context)


@login_required
def enable_2fa(request):
    """Включение 2FA"""
    # Проверяем есть ли уже устройство
    existing_device = TOTPDevice.objects.filter(user=request.user, confirmed=True).first()
    if existing_device:
        messages.info(request, '2FA уже включена')
        return redirect('accounts:security_settings')
    
    # Создаем новое устройство
    device = TOTPDevice.objects.create(
        user=request.user,
        name=f'LootLink-{request.user.username}',
        confirmed=False
    )
    
    # Генерируем QR код
    otpauth_url = device.config_url
    
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(otpauth_url)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Конвертируем в base64
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    img_str = base64.b64encode(buffer.getvalue()).decode()
    
    context = {
        'device': device,
        'qr_code': img_str,
        'secret': device.key,
    }
    return render(request, 'accounts/enable_2fa.html', context)


@login_required
@require_http_methods(['POST'])
def confirm_2fa(request):
    """Подтверждение 2FA кодом"""
    device_id = request.POST.get('device_id')
    token = request.POST.get('token', '').strip()
    
    try:
        device = TOTPDevice.objects.get(id=device_id, user=request.user, confirmed=False)
        
        if device.verify_token(token):
            device.confirmed = True
            device.save()
            
            messages.success(request, '✅ 2FA успешно включена!')
            return JsonResponse({'success': True})
        else:
            return JsonResponse({'success': False, 'error': 'Неверный код'})
            
    except TOTPDevice.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Устройство не найдено'})


@login_required
@require_http_methods(['POST'])
def disable_2fa(request):
    """Отключение 2FA"""
    password = request.POST.get('password')
    
    # Проверяем пароль
    if not request.user.check_password(password):
        return JsonResponse({'success': False, 'error': 'Неверный пароль'})
    
    # Удаляем все устройства
    TOTPDevice.objects.filter(user=request.user).delete()
    
    messages.success(request, '2FA отключена')
    return JsonResponse({'success': True})


@login_required
def login_history(request):
    """Полная история входов"""
    history = LoginHistory.objects.filter(
        user=request.user
    ).order_by('-created_at')
    
    # Статистика
    stats = {
        'total_logins': history.count(),
        'successful_logins': history.filter(success=True).count(),
        'failed_logins': history.filter(success=False).count(),
        'unique_ips': history.values('ip_address').distinct().count(),
    }
    
    context = {
        'history': history,
        'stats': stats,
    }
    return render(request, 'accounts/login_history.html', context)

