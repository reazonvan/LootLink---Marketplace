"""
Views для кастомной админ-панели
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import user_passes_test
from django.db.models import Count, Sum, Avg, Q
from django.utils import timezone
from datetime import timedelta

from accounts.models import CustomUser, Profile
from listings.models import Listing, Game, Category
from transactions.models import PurchaseRequest, Review
from core.models_audit import SecurityAuditLog, DataChangeLog
from listings.models_reports import Report
from transactions.models_disputes import Dispute


def is_staff_or_moderator(user):
    """Проверка: админ или модератор"""
    return user.is_staff or (hasattr(user, 'profile') and user.profile.is_moderator)


@user_passes_test(is_staff_or_moderator)
def dashboard(request):
    """
    Главная страница админ-панели с аналитикой
    """
    # Временные периоды
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    # ═══ ОБЩАЯ СТАТИСТИКА ═══
    total_users = CustomUser.objects.count()
    total_listings = Listing.objects.count()
    active_listings = Listing.objects.filter(status='active').count()
    total_transactions = PurchaseRequest.objects.filter(status='completed').count()
    
    # ═══ СТАТИСТИКА ЗА ПЕРИОДЫ ═══
    new_users_today = CustomUser.objects.filter(date_joined__date=today).count()
    new_users_week = CustomUser.objects.filter(date_joined__date__gte=week_ago).count()
    new_users_month = CustomUser.objects.filter(date_joined__date__gte=month_ago).count()
    
    new_listings_today = Listing.objects.filter(created_at__date=today).count()
    new_listings_week = Listing.objects.filter(created_at__date__gte=week_ago).count()
    
    completed_today = PurchaseRequest.objects.filter(
        status='completed', 
        updated_at__date=today
    ).count()
    completed_week = PurchaseRequest.objects.filter(
        status='completed',
        updated_at__date__gte=week_ago
    ).count()
    
    # ═══ МОДЕРАЦИЯ ═══
    pending_moderation = Listing.objects.filter(status='pending').count()
    pending_reports = Report.objects.filter(status='pending').count()
    active_disputes = Dispute.objects.filter(status__in=['pending', 'in_review']).count()
    
    # ═══ ФИНАНСЫ ═══
    total_balance = Profile.objects.aggregate(total=Sum('balance'))['total'] or 0
    avg_transaction = PurchaseRequest.objects.filter(
        status='completed'
    ).aggregate(avg=Avg('listing__price'))['avg'] or 0
    
    # ═══ БЕЗОПАСНОСТЬ ═══
    security_alerts_today = SecurityAuditLog.objects.filter(
        created_at__date=today,
        risk_level__in=['high', 'critical']
    ).count()
    
    failed_logins_today = SecurityAuditLog.objects.filter(
        created_at__date=today,
        action_type='failed_login'
    ).count()
    
    # ═══ ТОП КАТЕГОРИИ ═══
    top_games = Game.objects.annotate(
        listings_count=Count('listings')
    ).order_by('-listings_count')[:5]
    
    # ═══ ПОСЛЕДНИЕ АКТИВНОСТИ ═══
    recent_users = CustomUser.objects.select_related('profile').order_by('-date_joined')[:5]
    recent_listings = Listing.objects.select_related('game', 'seller').order_by('-created_at')[:5]
    recent_transactions = PurchaseRequest.objects.select_related(
        'buyer', 'listing'
    ).order_by('-created_at')[:5]
    
    # ═══ ДАННЫЕ ДЛЯ ГРАФИКОВ ═══
    # Регистрации по дням (последние 7 дней)
    registrations_chart = []
    for i in range(6, -1, -1):
        date = today - timedelta(days=i)
        count = CustomUser.objects.filter(date_joined__date=date).count()
        registrations_chart.append({
            'date': date.strftime('%d.%m'),
            'count': count
        })
    
    # Объявления по дням
    listings_chart = []
    for i in range(6, -1, -1):
        date = today - timedelta(days=i)
        count = Listing.objects.filter(created_at__date=date).count()
        listings_chart.append({
            'date': date.strftime('%d.%m'),
            'count': count
        })
    
    context = {
        # Общая статистика
        'total_users': total_users,
        'total_listings': total_listings,
        'active_listings': active_listings,
        'total_transactions': total_transactions,
        
        # За периоды
        'new_users_today': new_users_today,
        'new_users_week': new_users_week,
        'new_users_month': new_users_month,
        'new_listings_today': new_listings_today,
        'new_listings_week': new_listings_week,
        'completed_today': completed_today,
        'completed_week': completed_week,
        
        # Модерация
        'pending_moderation': pending_moderation,
        'pending_reports': pending_reports,
        'active_disputes': active_disputes,
        
        # Финансы
        'total_balance': total_balance,
        'avg_transaction': avg_transaction,
        
        # Безопасность
        'security_alerts_today': security_alerts_today,
        'failed_logins_today': failed_logins_today,
        
        # Топы
        'top_games': top_games,
        
        # Последние
        'recent_users': recent_users,
        'recent_listings': recent_listings,
        'recent_transactions': recent_transactions,
        
        # Графики
        'registrations_chart': registrations_chart,
        'listings_chart': listings_chart,
    }
    
    return render(request, 'admin_panel/dashboard.html', context)


@user_passes_test(is_staff_or_moderator)
def users_list(request):
    """Список пользователей с фильтрами"""
    users = CustomUser.objects.select_related('profile').all()
    
    # Фильтры
    role = request.GET.get('role')
    verified = request.GET.get('verified')
    search = request.GET.get('search')
    
    if role == 'admin':
        users = users.filter(is_staff=True)
    elif role == 'moderator':
        users = users.filter(profile__is_moderator=True)
    elif role == 'verified':
        users = users.filter(profile__is_verified=True)
    
    if verified == 'yes':
        users = users.filter(profile__is_verified=True)
    elif verified == 'no':
        users = users.filter(profile__is_verified=False)
    
    if search:
        users = users.filter(
            Q(username__icontains=search) |
            Q(email__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search)
        )
    
    users = users.order_by('-date_joined')
    
    context = {
        'users': users,
        'total_count': users.count(),
        'filters': {
            'role': role,
            'verified': verified,
            'search': search,
        }
    }
    
    return render(request, 'admin_panel/users_list.html', context)


@user_passes_test(is_staff_or_moderator)
def user_detail(request, user_id):
    """Детальная информация о пользователе"""
    user = get_object_or_404(CustomUser.objects.select_related('profile'), id=user_id)
    
    # Статистика пользователя
    user_listings = Listing.objects.filter(seller=user).count()
    user_purchases = PurchaseRequest.objects.filter(buyer=user, status='completed').count()
    user_sales = PurchaseRequest.objects.filter(listing__seller=user, status='completed').count()
    
    # Последняя активность
    recent_listings = Listing.objects.filter(seller=user).order_by('-created_at')[:5]
    recent_purchases = PurchaseRequest.objects.filter(buyer=user).order_by('-created_at')[:5]
    
    # Логи безопасности
    security_logs = SecurityAuditLog.objects.filter(user=user).order_by('-created_at')[:10]
    
    context = {
        'user': user,
        'user_listings': user_listings,
        'user_purchases': user_purchases,
        'user_sales': user_sales,
        'recent_listings': recent_listings,
        'recent_purchases': recent_purchases,
        'security_logs': security_logs,
    }
    
    return render(request, 'admin_panel/user_detail.html', context)


@user_passes_test(is_staff_or_moderator)
def listings_moderation(request):
    """Модерация объявлений"""
    listings = Listing.objects.select_related('game', 'category', 'seller__profile').all()
    
    # Фильтры
    status = request.GET.get('status')
    game = request.GET.get('game')
    search = request.GET.get('search')
    
    if status:
        listings = listings.filter(status=status)
    else:
        # По умолчанию показываем только ожидающие модерации
        listings = listings.filter(status='pending')
    
    if game:
        listings = listings.filter(game_id=game)
    
    if search:
        listings = listings.filter(
            Q(title__icontains=search) |
            Q(description__icontains=search) |
            Q(seller__username__icontains=search)
        )
    
    listings = listings.order_by('-created_at')
    
    # Для фильтра игр
    games = Game.objects.all().order_by('name')
    
    context = {
        'listings': listings,
        'total_count': listings.count(),
        'games': games,
        'filters': {
            'status': status,
            'game': game,
            'search': search,
        }
    }
    
    return render(request, 'admin_panel/listings_moderation.html', context)


@user_passes_test(is_staff_or_moderator)
def listing_detail(request, listing_id):
    """Детальный просмотр объявления для модерации"""
    listing = get_object_or_404(
        Listing.objects.select_related('game', 'category', 'seller__profile'),
        id=listing_id
    )
    
    # Репорты на это объявление
    reports = Report.objects.filter(listing=listing).select_related('reporter')
    
    context = {
        'listing': listing,
        'reports': reports,
    }
    
    return render(request, 'admin_panel/listing_detail.html', context)


@user_passes_test(is_staff_or_moderator)
def transactions_list(request):
    """Список транзакций"""
    transactions = PurchaseRequest.objects.select_related(
        'buyer__profile', 'listing__seller__profile', 'listing__game'
    ).all()
    
    # Фильтры
    status = request.GET.get('status')
    search = request.GET.get('search')
    
    if status:
        transactions = transactions.filter(status=status)
    
    if search:
        transactions = transactions.filter(
            Q(buyer__username__icontains=search) |
            Q(listing__seller__username__icontains=search) |
            Q(listing__title__icontains=search)
        )
    
    transactions = transactions.order_by('-created_at')
    
    context = {
        'transactions': transactions,
        'total_count': transactions.count(),
        'filters': {
            'status': status,
            'search': search,
        }
    }
    
    return render(request, 'admin_panel/transactions_list.html', context)


@user_passes_test(is_staff_or_moderator)
def transaction_detail(request, transaction_id):
    """Детальная информация о транзакции"""
    transaction = get_object_or_404(
        PurchaseRequest.objects.select_related(
            'buyer__profile', 'listing__seller__profile', 'listing__game'
        ),
        id=transaction_id
    )
    
    context = {
        'transaction': transaction,
    }
    
    return render(request, 'admin_panel/transaction_detail.html', context)


@user_passes_test(is_staff_or_moderator)
def disputes_list(request):
    """Список споров"""
    disputes = Dispute.objects.select_related(
        'purchase_request__buyer',
        'purchase_request__listing__seller',
        'purchase_request__listing'
    ).all()
    
    # Фильтры
    status = request.GET.get('status', 'pending')
    
    if status:
        if status == 'active':
            disputes = disputes.filter(status__in=['pending', 'in_review'])
        else:
            disputes = disputes.filter(status=status)
    
    disputes = disputes.order_by('-created_at')
    
    context = {
        'disputes': disputes,
        'total_count': disputes.count(),
        'filters': {
            'status': status,
        }
    }
    
    return render(request, 'admin_panel/disputes_list.html', context)


@user_passes_test(is_staff_or_moderator)
def dispute_detail(request, dispute_id):
    """Детальная информация о споре"""
    dispute = get_object_or_404(
        Dispute.objects.select_related(
            'purchase_request__buyer__profile',
            'purchase_request__listing__seller__profile',
            'purchase_request__listing__game',
            'resolved_by'
        ).prefetch_related('evidence'),
        id=dispute_id
    )
    
    context = {
        'dispute': dispute,
    }
    
    return render(request, 'admin_panel/dispute_detail.html', context)


@user_passes_test(is_staff_or_moderator)
def reports_list(request):
    """Список жалоб"""
    reports = Report.objects.select_related(
        'listing__seller', 'listing__game', 'reporter'
    ).all()
    
    # Фильтры
    status = request.GET.get('status', 'pending')
    
    if status:
        reports = reports.filter(status=status)
    
    reports = reports.order_by('-created_at')
    
    context = {
        'reports': reports,
        'total_count': reports.count(),
        'filters': {
            'status': status,
        }
    }
    
    return render(request, 'admin_panel/reports_list.html', context)


@user_passes_test(is_staff_or_moderator)
def security_logs(request):
    """Логи безопасности"""
    logs = SecurityAuditLog.objects.select_related('user').all()
    
    # Фильтры
    risk_level = request.GET.get('risk_level')
    action_type = request.GET.get('action_type')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if risk_level:
        logs = logs.filter(risk_level=risk_level)
    
    if action_type:
        logs = logs.filter(action_type=action_type)
    
    if date_from:
        logs = logs.filter(created_at__date__gte=date_from)
    
    if date_to:
        logs = logs.filter(created_at__date__lte=date_to)
    
    logs = logs.order_by('-created_at')[:100]
    
    context = {
        'logs': logs,
        'total_count': logs.count(),
        'filters': {
            'risk_level': risk_level,
            'action_type': action_type,
            'date_from': date_from,
            'date_to': date_to,
        }
    }
    
    return render(request, 'admin_panel/security_logs.html', context)


@staff_member_required
def settings(request):
    """Настройки админ-панели"""
    from django.conf import settings as django_settings
    
    context = {
        'debug': django_settings.DEBUG,
        'allowed_hosts': django_settings.ALLOWED_HOSTS,
        'database': django_settings.DATABASES['default']['ENGINE'],
        'redis_enabled': django_settings.USE_REDIS,
    }
    
    return render(request, 'admin_panel/settings.html', context)

