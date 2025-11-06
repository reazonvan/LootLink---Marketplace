"""
Дашборд аналитики для продавцов и покупателей.
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum, Avg, Q
from django.utils import timezone
from datetime import timedelta
from listings.models import Listing
from transactions.models import PurchaseRequest, Review
from decimal import Decimal
import json


@login_required
def analytics_dashboard(request):
    """Дашборд аналитики пользователя"""
    user = request.user
    
    # Период для статистики
    period = request.GET.get('period', '30')  # дней
    try:
        days = int(period)
    except:
        days = 30
    
    start_date = timezone.now() - timedelta(days=days)
    
    # === СТАТИСТИКА ПРОДАЖ ===
    sales_stats = {
        'total_sales': PurchaseRequest.objects.filter(
            seller=user,
            status='completed'
        ).count(),
        
        'total_revenue': PurchaseRequest.objects.filter(
            seller=user,
            status='completed',
            completed_at__gte=start_date
        ).aggregate(
            total=Sum('listing__price')
        )['total'] or Decimal('0.00'),
        
        'avg_price': Listing.objects.filter(
            seller=user,
            status__in=['active', 'sold']
        ).aggregate(avg=Avg('price'))['avg'] or Decimal('0.00'),
        
        'active_listings': Listing.objects.filter(
            seller=user,
            status='active'
        ).count(),
    }
    
    # === СТАТИСТИКА ПОКУПОК ===
    purchase_stats = {
        'total_purchases': PurchaseRequest.objects.filter(
            buyer=user,
            status='completed'
        ).count(),
        
        'total_spent': PurchaseRequest.objects.filter(
            buyer=user,
            status='completed',
            completed_at__gte=start_date
        ).aggregate(
            total=Sum('listing__price')
        )['total'] or Decimal('0.00'),
    }
    
    # === ГРАФИК ПРОДАЖ ПО ДНЯМ ===
    sales_by_day = []
    for i in range(days):
        date = timezone.now().date() - timedelta(days=days-i-1)
        count = PurchaseRequest.objects.filter(
            seller=user,
            status='completed',
            completed_at__date=date
        ).count()
        sales_by_day.append({
            'date': date.strftime('%d.%m'),
            'count': count
        })
    
    # === ПОПУЛЯРНЫЕ ТОВАРЫ ===
    popular_listings = Listing.objects.filter(
        seller=user
    ).annotate(
        views_count=Count('id')  # Можно добавить поле views в модель
    ).order_by('-views_count')[:5]
    
    # === ОТЗЫВЫ ===
    reviews_stats = {
        'total_reviews': Review.objects.filter(reviewed_user=user).count(),
        'avg_rating': Review.objects.filter(reviewed_user=user).aggregate(
            avg=Avg('rating')
        )['avg'] or 0,
        'recent_reviews': Review.objects.filter(
            reviewed_user=user
        ).select_related('reviewer').order_by('-created_at')[:5]
    }
    
    context = {
        'sales_stats': sales_stats,
        'purchase_stats': purchase_stats,
        'sales_by_day_json': json.dumps(sales_by_day),
        'popular_listings': popular_listings,
        'reviews_stats': reviews_stats,
        'period': period,
    }
    
    return render(request, 'accounts/analytics_dashboard.html', context)


@login_required
def export_data(request):
    """Экспорт данных в CSV"""
    import csv
    from django.http import HttpResponse
    
    data_type = request.GET.get('type', 'sales')
    
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = f'attachment; filename="lootlink_{data_type}.csv"'
    response.write('\ufeff')  # BOM для правильного отображения в Excel
    
    writer = csv.writer(response)
    
    if data_type == 'sales':
        writer.writerow(['Дата', 'Товар', 'Покупатель', 'Цена', 'Статус'])
        
        sales = PurchaseRequest.objects.filter(
            seller=request.user
        ).select_related('listing', 'buyer').order_by('-created_at')
        
        for sale in sales:
            writer.writerow([
                sale.created_at.strftime('%d.%m.%Y %H:%M'),
                sale.listing.title,
                sale.buyer.username,
                str(sale.listing.price),
                sale.get_status_display()
            ])
    
    elif data_type == 'purchases':
        writer.writerow(['Дата', 'Товар', 'Продавец', 'Цена', 'Статус'])
        
        purchases = PurchaseRequest.objects.filter(
            buyer=request.user
        ).select_related('listing', 'seller').order_by('-created_at')
        
        for purchase in purchases:
            writer.writerow([
                purchase.created_at.strftime('%d.%m.%Y %H:%M'),
                purchase.listing.title,
                purchase.seller.username,
                str(purchase.listing.price),
                purchase.get_status_display()
            ])
    
    elif data_type == 'listings':
        writer.writerow(['Название', 'Игра', 'Цена', 'Статус', 'Дата создания'])
        
        listings = Listing.objects.filter(
            seller=request.user
        ).select_related('game').order_by('-created_at')
        
        for listing in listings:
            writer.writerow([
                listing.title,
                listing.game.name,
                str(listing.price),
                listing.get_status_display(),
                listing.created_at.strftime('%d.%m.%Y %H:%M')
            ])
    
    return response

