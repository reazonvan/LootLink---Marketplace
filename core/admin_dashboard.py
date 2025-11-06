"""
Кастомный дашборд для админ-панели.
"""
from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count, Sum, Avg, Q
from django.utils import timezone
from datetime import timedelta
from accounts.models import CustomUser, Profile
from listings.models import Listing, Game
from transactions.models import PurchaseRequest, Review
from chat.models import Message
from core.models import Notification
import json


@staff_member_required
def admin_dashboard(request):
    """
    Кастомный дашборд администратора с аналитикой.
    """
    # Период
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    # === ОБЩАЯ СТАТИСТИКА ===
    stats = {
        'total_users': CustomUser.objects.count(),
        'new_users_week': CustomUser.objects.filter(date_joined__gte=week_ago).count(),
        'verified_users': Profile.objects.filter(is_verified=True).count(),
        
        'total_listings': Listing.objects.count(),
        'active_listings': Listing.objects.filter(status='active').count(),
        'new_listings_week': Listing.objects.filter(created_at__date__gte=week_ago).count(),
        
        'total_transactions': PurchaseRequest.objects.count(),
        'completed_transactions': PurchaseRequest.objects.filter(status='completed').count(),
        'pending_transactions': PurchaseRequest.objects.filter(status='pending').count(),
        
        'total_messages': Message.objects.count(),
        'messages_today': Message.objects.filter(created_at__date=today).count(),
    }
    
    # === ФИНАНСЫ ===
    finance_stats = {
        'total_gmv': PurchaseRequest.objects.filter(
            status='completed'
        ).aggregate(
            total=Sum('listing__price')
        )['total'] or 0,
        
        'gmv_month': PurchaseRequest.objects.filter(
            status='completed',
            completed_at__gte=month_ago
        ).aggregate(
            total=Sum('listing__price')
        )['total'] or 0,
    }
    
    # === ТОП ИГРЫ ===
    top_games = Game.objects.annotate(
        listing_count=Count('listings', filter=Q(listings__status='active'))
    ).order_by('-listing_count')[:5]
    
    # === ТОП ПРОДАВЦЫ ===
    top_sellers = Profile.objects.annotate(
        sales_count=Count('user__sales', filter=Q(user__sales__status='completed'))
    ).filter(sales_count__gt=0).order_by('-sales_count', '-rating')[:5]
    
    # === АКТИВНОСТЬ ПО ДНЯМ (последние 7 дней) ===
    activity_data = []
    for i in range(7):
        date = today - timedelta(days=6-i)
        activity_data.append({
            'date': date.strftime('%d.%m'),
            'users': CustomUser.objects.filter(date_joined__date=date).count(),
            'listings': Listing.objects.filter(created_at__date=date).count(),
            'transactions': PurchaseRequest.objects.filter(created_at__date=date).count(),
        })
    
    # === ПОСЛЕДНИЕ ДЕЙСТВИЯ ===
    recent_users = CustomUser.objects.order_by('-date_joined')[:5]
    recent_listings = Listing.objects.select_related('seller', 'game').order_by('-created_at')[:5]
    recent_reviews = Review.objects.select_related('reviewer', 'reviewed_user').order_by('-created_at')[:5]
    
    context = {
        'stats': stats,
        'finance_stats': finance_stats,
        'top_games': top_games,
        'top_sellers': top_sellers,
        'activity_data_json': json.dumps(activity_data),
        'recent_users': recent_users,
        'recent_listings': recent_listings,
        'recent_reviews': recent_reviews,
    }
    
    return render(request, 'admin/custom_dashboard.html', context)


@staff_member_required
def system_logs(request):
    """Системные логи"""
    import os
    from django.conf import settings
    
    log_file = settings.BASE_DIR / 'logs' / 'lootlink.log'
    
    logs = []
    if os.path.exists(log_file):
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            logs = lines[-100:]  # Последние 100 строк
            logs.reverse()
    
    context = {
        'logs': logs
    }
    return render(request, 'admin/system_logs.html', context)

