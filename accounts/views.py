from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.db.models import Avg
from django.core.mail import send_mail
from django.conf import settings
from django.utils.http import url_has_allowed_host_and_scheme
from .forms import (CustomUserCreationForm, CustomAuthenticationForm, ProfileUpdateForm,
                    PasswordResetRequestForm, PasswordResetConfirmForm, ChangePasswordForm)
from .models import CustomUser, Profile, PasswordResetCode
from .models_security import LoginHistory
from transactions.models import Review


def _get_client_ip(request):
    from core.utils import get_client_ip
    return get_client_ip(request)


def register(request):
    """Регистрация нового пользователя."""
    if request.user.is_authenticated:
        return redirect('listings:home')
    
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Explicit backend is required because multiple auth backends are configured.
            login(request, user, backend='accounts.backends.CaseInsensitiveModelBackend')
            messages.success(request, 'Регистрация прошла успешно! Добро пожаловать в LootLink!')
            return redirect('listings:home')
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'accounts/register.html', {'form': form})


def user_login(request):
    """Вход пользователя в систему."""
    if request.user.is_authenticated:
        return redirect('listings:home')
    
    # Единая статистика платформы для консистентности с главной страницей.
    from core.utils import get_platform_stats
    platform_stats = get_platform_stats()
    total_users = platform_stats['active_users']
    total_deals = platform_stats['total_deals']
    
    if request.method == 'POST':
        try:
            form = CustomAuthenticationForm(request, data=request.POST)
            if form.is_valid():
                username = form.cleaned_data.get('username')
                password = form.cleaned_data.get('password')
                user = authenticate(username=username, password=password)
                if user is not None:
                    login(request, user)
                    messages.success(request, f'Добро пожаловать, {username}!')
                    # Безопасное перенаправление только на внутренние URL
                    next_page = request.POST.get('next') or request.GET.get('next')
                    if next_page and url_has_allowed_host_and_scheme(
                        url=next_page,
                        allowed_hosts={request.get_host()},
                        require_https=request.is_secure(),
                    ):
                        return redirect(next_page)
                    return redirect('listings:home')
                else:
                    messages.error(request, 'Неверное имя пользователя или пароль.')
            else:
                # Если форма невалидна, показываем ошибки
                messages.error(request, 'Неверное имя пользователя или пароль.')
        except Exception as e:
            # Логируем ошибку и показываем пользователю понятное сообщение
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f'Ошибка при входе: {e}')
            messages.error(request, 'Произошла ошибка при входе. Попробуйте еще раз.')
            form = CustomAuthenticationForm()
    else:
        form = CustomAuthenticationForm()
    
    from listings.models import Game
    total_games = Game.objects.filter(is_active=True).count()

    context = {
        'form': form,
        'total_users': total_users,
        'total_deals': total_deals,
        'total_games': total_games,
    }
    return render(request, 'accounts/login.html', context)


@login_required
@require_POST
def user_logout(request):
    """Выход пользователя из системы."""
    logout(request)
    messages.info(request, 'Вы вышли из системы.')
    return redirect('listings:home')


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
            messages.info(request, 'Профиль был создан автоматически.')
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'Ошибка при создании профиля для {username}: {e}')
        messages.error(request, 'Произошла ошибка при загрузке профиля.')
        return redirect('listings:home')
    
    # Получаем отзывы о пользователе с оптимизацией
    reviews = Review.objects.filter(reviewed_user=user)\
        .select_related('reviewer', 'reviewer__profile', 'purchase_request', 'purchase_request__listing')\
        .order_by('-created_at')
    
    # Добавляем пагинацию для отзывов
    paginator = Paginator(reviews, 10)  # 10 отзывов на страницу
    page_number = request.GET.get('page')
    reviews_page = paginator.get_page(page_number)
    
    # Статистика
    is_own_profile = request.user == user
    
    context = {
        'profile_user': user,
        'profile': profile,
        'reviews': reviews_page,
        'is_own_profile': is_own_profile,
    }
    
    return render(request, 'accounts/profile.html', context)


@login_required
def profile_edit(request):
    """
    Редактирование профиля.
    
    ВАЖНО: Username, Email и Phone нельзя изменить.
    Редактируется только дополнительная информация профиля.
    """
    # Проверяем наличие профиля
    profile, created = Profile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        profile_form = ProfileUpdateForm(
            request.POST,
            request.FILES,
            instance=request.user.profile
        )
        
        if profile_form.is_valid():
            profile_form.save()
            messages.success(request, 'Профиль успешно обновлен!')
            return redirect('accounts:profile', username=request.user.username)
    else:
        profile_form = ProfileUpdateForm(instance=request.user.profile)
    
    context = {
        'profile_form': profile_form,
    }
    
    return render(request, 'accounts/profile_edit.html', context)


@login_required
def my_listings(request):
    """Мои объявления с оптимизацией запросов."""
    from listings.models import Listing
    from django.core.paginator import Paginator
    
    # Оптимизация: используем select_related для избежания N+1 запросов
    listings = Listing.objects.filter(seller=request.user)\
        .select_related('game')\
        .order_by('-created_at')
    
    # Пагинация
    paginator = Paginator(listings, 20)  # 20 объявлений на страницу
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
    }
    
    return render(request, 'accounts/my_listings.html', context)


@login_required
def my_purchases(request):
    """Мои покупки с оптимизацией запросов."""
    from transactions.models import PurchaseRequest
    from django.core.paginator import Paginator
    
    # Оптимизация: добавляем game для listing
    purchases = PurchaseRequest.objects.filter(
        buyer=request.user
    ).select_related('listing', 'listing__game', 'seller', 'seller__profile')\
     .order_by('-created_at')
    
    # Пагинация
    paginator = Paginator(purchases, 20)  # 20 покупок на страницу
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
    }
    
    return render(request, 'accounts/my_purchases.html', context)


@login_required
def my_sales(request):
    """Мои продажи с оптимизацией запросов."""
    from transactions.models import PurchaseRequest
    from django.core.paginator import Paginator
    
    # Оптимизация: добавляем game для listing и profile для buyer
    sales = PurchaseRequest.objects.filter(
        seller=request.user
    ).select_related('listing', 'listing__game', 'buyer', 'buyer__profile')\
     .order_by('-created_at')
    
    # Пагинация
    paginator = Paginator(sales, 20)  # 20 продаж на страницу
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
    }
    
    return render(request, 'accounts/my_sales.html', context)


def password_reset_request(request):
    """Запрос на сброс пароля - отправка кода на email и SMS."""
    if request.method == 'POST':
        # Rate limiting: 3 запроса за 10 минут на IP
        from django.core.cache import cache
        ip = _get_client_ip(request)
        cache_key = f'password_reset_rate_{ip}'
        attempts = cache.get(cache_key, 0)
        if attempts >= 3:
            messages.error(request, 'Слишком много запросов. Подождите 10 минут.')
            return render(request, 'accounts/password_reset_request.html',
                          {'form': PasswordResetRequestForm()})
        cache.set(cache_key, attempts + 1, 600)

        form = PasswordResetRequestForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            user = CustomUser.objects.get(email=email)
            
            # Создаём код сброса
            reset_code = PasswordResetCode.create_code(user)
            
            # Отправляем email с кодом
            subject = 'Код сброса пароля - LootLink'
            email_message = f"""
Здравствуйте, {user.username}!

Вы запросили сброс пароля на сайте LootLink.

Ваш код подтверждения: {reset_code.code}

Код действителен в течение 15 минут.

Если вы не запрашивали сброс пароля, проигнорируйте это письмо.

С уважением,
Команда LootLink
            """
            
            email_sent = False
            sms_sent = False
            
            # Отправляем email через EmailService (с HTML и лучшей обработкой ошибок)
            try:
                from core.email_service import EmailService
                email_sent = EmailService.send_password_reset_email(user, reset_code.code)
                
                if not email_sent:
                    # Fallback на старый способ
                    send_mail(
                        subject,
                        email_message,
                        settings.DEFAULT_FROM_EMAIL,
                        [email],
                        fail_silently=False,
                    )
                    email_sent = True
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f'Ошибка отправки email: {e}')
                
                # Логируем в audit
                from core.models_audit import SecurityAuditLog
                SecurityAuditLog.log(
                    action_type='password_reset_request',
                    user=user,
                    description=f'Ошибка отправки email при сбросе пароля: {str(e)}',
                    risk_level='medium',
                    request=request
                )
            
            # Отправляем СМС если у пользователя указан телефон
            if user.profile.phone:
                try:
                    from core.sms_service import send_password_reset_sms
                    sms_sent = send_password_reset_sms(
                        user.profile.phone, 
                        reset_code.code,
                        user.username
                    )
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f'Ошибка отправки СМС: {e}')
            
            # Формируем сообщение пользователю
            if email_sent and sms_sent:
                messages.success(request, f'Код отправлен на {email} и {user.profile.phone}')
            elif email_sent:
                messages.success(request, f'Код отправлен на {email}')
            elif sms_sent:
                messages.success(request, f'Код отправлен на {user.profile.phone}')
            else:
                messages.warning(request, 'Код создан, но возникли проблемы с отправкой. Проверьте консоль сервера.')
            
            request.session['reset_email'] = email
            return redirect('accounts:password_reset_confirm')
    else:
        form = PasswordResetRequestForm()
    
    context = {
        'form': form,
    }
    
    return render(request, 'accounts/password_reset_request.html', context)


def verify_email(request, token):
    """Верификация email адреса по токену."""
    from .models import EmailVerification
    from django.utils import timezone
    from datetime import timedelta
    
    try:
        verification = EmailVerification.objects.get(token=token)
        
        # Проверяем что токен не старше 24 часов
        if verification.created_at < timezone.now() - timedelta(hours=24):
            messages.error(request, 'Ссылка верификации истекла. Запросите новую.')
            return redirect('accounts:login')
        
        # Проверяем что еще не верифицирован
        if verification.is_verified:
            messages.info(request, 'Email уже подтвержден.')
            return redirect('accounts:login')
        
        # Верифицируем
        verification.verify()
        
        messages.success(request, 'Email успешно подтвержден! Теперь вы можете войти.')
        return redirect('accounts:login')
        
    except EmailVerification.DoesNotExist:
        messages.error(request, 'Неверная ссылка верификации.')
        return redirect('accounts:login')


def resend_verification_email(request):
    """Повторная отправка письма верификации."""
    if not request.user.is_authenticated:
        messages.error(request, 'Войдите в систему для повторной отправки письма.')
        return redirect('accounts:login')
    
    from .models import EmailVerification
    from django.core.mail import send_mail
    from django.conf import settings
    from django.urls import reverse
    
    # Проверяем что email еще не верифицирован
    try:
        verification = request.user.email_verification
        if verification.is_verified:
            messages.info(request, 'Ваш email уже подтвержден.')
            return redirect('accounts:profile', username=request.user.username)
    except EmailVerification.DoesNotExist:
        # Создаем новую верификацию
        verification = EmailVerification.create_for_user(request.user)
    
    # Отправляем письмо
    domain = settings.SITE_URL.replace('http://', '').replace('https://', '')
    protocol = 'https' if not settings.DEBUG else 'http'
    verification_url = f"{protocol}://{domain}{reverse('accounts:verify_email', kwargs={'token': verification.token})}"
    
    subject = 'Подтвердите ваш email - LootLink'
    message = f"""
Здравствуйте, {request.user.username}!

Перейдите по ссылке для подтверждения email:

{verification_url}

Ссылка действительна в течение 24 часов.

С уважением,
Команда LootLink
"""
    
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [request.user.email],
            fail_silently=False
        )
        messages.success(request, f'Письмо с подтверждением отправлено на {request.user.email}')
    except Exception as e:
        messages.error(request, f'Ошибка отправки письма: {e}')
    
    return redirect('accounts:profile', username=request.user.username)


def password_reset_confirm(request):
    """Подтверждение сброса пароля с вводом кода."""
    email = request.session.get('reset_email')
    if not email:
        messages.error(request, 'Сессия истекла. Запросите код заново.')
        return redirect('accounts:password_reset_request')
    
    try:
        user = CustomUser.objects.get(email=email)
    except CustomUser.DoesNotExist:
        messages.error(request, 'Пользователь не найден.')
        return redirect('accounts:password_reset_request')
    
    if request.method == 'POST':
        form = PasswordResetConfirmForm(request.POST, user=user)
        if form.is_valid():
            form.save()
            del request.session['reset_email']
            messages.success(request, 'Пароль успешно изменён! Войдите с новым паролем.')
            return redirect('accounts:login')
    else:
        form = PasswordResetConfirmForm(user=user)
    
    context = {
        'form': form,
        'email': email,
    }
    
    return render(request, 'accounts/password_reset_confirm.html', context)


def check_username_available(request):
    """AJAX endpoint для проверки доступности никнейма."""
    from django.http import JsonResponse
    from core.decorators import api_rate_limit
    from django.core.cache import cache
    
    # Rate limiting: 30 запросов в минуту на IP
    ip = _get_client_ip(request)
    cache_key = f'username_check_rate_{ip}'
    requests_count = cache.get(cache_key, 0)
    
    if requests_count >= 30:
        return JsonResponse({
            'available': False, 
            'message': 'Слишком много запросов. Подождите минуту.'
        }, status=429)
    
    cache.set(cache_key, requests_count + 1, 60)
    
    username = request.GET.get('username', '').strip()
    
    if not username:
        return JsonResponse({'available': False, 'message': 'Введите имя пользователя'})
    
    if len(username) < 3:
        return JsonResponse({'available': False, 'message': 'Минимум 3 символа'})
    
    if len(username) > 150:
        return JsonResponse({'available': False, 'message': 'Максимум 150 символов'})
    
    # Проверяем что username содержит только допустимые символы
    import re
    if not re.match(r'^[\w.@+-]+$', username):
        return JsonResponse({'available': False, 'message': 'Недопустимые символы. Разрешены: буквы, цифры, @/./+/-/_'})
    
    # Case-insensitive проверка (argear = Argear)
    exists = CustomUser.objects.filter(username__iexact=username).exists()
    
    if exists:
        return JsonResponse({'available': False, 'message': 'Этот никнейм уже занят'})
    
    return JsonResponse({'available': True, 'message': 'Никнейм доступен'})


def check_email_available(request):
    """AJAX endpoint для проверки доступности email."""
    from django.http import JsonResponse
    from django.core.cache import cache
    
    # Rate limiting: 30 запросов в минуту на IP
    ip = _get_client_ip(request)
    cache_key = f'email_check_rate_{ip}'
    requests_count = cache.get(cache_key, 0)
    
    if requests_count >= 30:
        return JsonResponse({
            'available': False, 
            'message': 'Слишком много запросов. Подождите минуту.'
        }, status=429)
    
    cache.set(cache_key, requests_count + 1, 60)
    
    email = request.GET.get('email', '').strip()
    
    if not email:
        return JsonResponse({'available': False, 'message': 'Введите email'})
    
    # Простая валидация email
    import re
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email):
        return JsonResponse({'available': False, 'message': 'Некорректный формат email'})
    
    exists = CustomUser.objects.filter(email__iexact=email).exists()

    if exists:
        return JsonResponse({'available': False, 'message': 'Этот email уже зарегистрирован'})
    
    return JsonResponse({'available': True, 'message': 'Email доступен'})


def check_phone_available(request):
    """AJAX endpoint для проверки доступности телефона."""
    from django.http import JsonResponse
    from django.core.cache import cache
    
    # Rate limiting: 30 запросов в минуту на IP
    ip = _get_client_ip(request)
    cache_key = f'phone_check_rate_{ip}'
    requests_count = cache.get(cache_key, 0)
    
    if requests_count >= 30:
        return JsonResponse({
            'available': False, 
            'message': 'Слишком много запросов. Подождите минуту.'
        }, status=429)
    
    cache.set(cache_key, requests_count + 1, 60)
    
    phone = request.GET.get('phone', '').strip()
    
    if not phone:
        return JsonResponse({'available': False, 'message': 'Введите номер телефона'})
    
    # Проверка формата
    import re
    phone_digits = re.sub(r'\D', '', phone)
    
    if len(phone_digits) < 10 or len(phone_digits) > 11:
        return JsonResponse({'available': False, 'message': 'Некорректный номер телефона'})
    
    exists = Profile.objects.filter(phone=phone).exists()
    
    if exists:
        return JsonResponse({'available': False, 'message': 'Этот номер уже зарегистрирован'})
    
    return JsonResponse({'available': True, 'message': 'Номер доступен'})


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

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'change_password':
            password_form = ChangePasswordForm(request.POST, user=user)
            if password_form.is_valid():
                password_form.save()
                from django.contrib.auth import update_session_auth_hash
                update_session_auth_hash(request, user)
                messages.success(request, 'Пароль успешно изменён.')
                password_changed = True
                password_form = ChangePasswordForm(user=user)

    # Активные сессии
    current_session_key = request.session.session_key
    sessions = Session.objects.filter(expire_date__gte=timezone.now())
    user_sessions = []
    for session in sessions:
        data = session.get_decoded()
        if str(data.get('_auth_user_id')) == str(user.pk):
            user_sessions.append({
                'session_key': session.session_key,
                'expire_date': session.expire_date,
                'is_current': session.session_key == current_session_key,
            })

    # Последние входы (с устройствами)
    recent_logins = LoginHistory.objects.filter(
        user=user, success=True
    ).order_by('-created_at')[:20]

    context = {
        'profile': profile,
        'has_2fa': has_2fa,
        'password_form': password_form,
        'password_changed': password_changed,
        'user_sessions': user_sessions,
        'recent_logins': recent_logins,
        'active_tab': request.GET.get('tab', 'account'),
    }
    return render(request, 'accounts/settings.html', context)


@login_required
@require_POST
def terminate_session(request):
    """Завершить конкретную сессию."""
    from django.contrib.sessions.models import Session
    session_key = request.POST.get('session_key')
    if session_key == request.session.session_key:
        messages.error(request, 'Нельзя завершить текущую сессию.')
        return redirect('accounts:account_settings')
    try:
        session = Session.objects.get(session_key=session_key)
        data = session.get_decoded()
        if str(data.get('_auth_user_id')) == str(request.user.pk):
            session.delete()
            messages.success(request, 'Сессия завершена.')
        else:
            messages.error(request, 'Нет доступа к этой сессии.')
    except Session.DoesNotExist:
        messages.error(request, 'Сессия не найдена.')
    return redirect('accounts:account_settings')


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
        if str(data.get('_auth_user_id')) == str(request.user.pk):
            session.delete()
            count += 1
    messages.success(request, f'Завершено сессий: {count}')
    return redirect('accounts:account_settings')
