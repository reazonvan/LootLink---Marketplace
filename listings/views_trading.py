"""
Views для торговли: торг, резерв.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from .models import Listing
from .models_trading import PriceOffer, ListingReservation, PriceHistory
from decimal import Decimal


@login_required
@require_http_methods(['POST'])
def make_price_offer(request, listing_id):
    """Сделать предложение цены"""
    listing = get_object_or_404(Listing, id=listing_id, status='active')
    
    # Нельзя торговаться за свое объявление
    if listing.seller == request.user:
        return JsonResponse({'success': False, 'error': 'Нельзя торговаться за свое объявление'})
    
    offered_price = request.POST.get('offered_price')
    message = request.POST.get('message', '')
    
    try:
        offered_price = Decimal(offered_price)
        
        if offered_price <= 0:
            return JsonResponse({'success': False, 'error': 'Цена должна быть больше 0'})
        
        if offered_price >= listing.price:
            return JsonResponse({'success': False, 'error': 'Предложите цену ниже текущей'})
        
        # Проверяем что нет активного предложения
        existing_offer = PriceOffer.objects.filter(
            listing=listing,
            buyer=request.user,
            status='pending'
        ).first()
        
        if existing_offer:
            return JsonResponse({'success': False, 'error': 'У вас уже есть активное предложение'})
        
        # Создаем предложение
        offer = PriceOffer.objects.create(
            listing=listing,
            buyer=request.user,
            seller=listing.seller,
            offered_price=offered_price,
            original_price=listing.price,
            message=message,
            expires_at=timezone.now() + timezone.timedelta(days=3)
        )
        
        # Уведомляем продавца
        from core.services import NotificationService
        NotificationService.notify_price_offer(offer)
        
        return JsonResponse({
            'success': True,
            'message': 'Предложение отправлено продавцу',
            'offer_id': offer.id
        })
        
    except (ValueError, TypeError) as e:
        return JsonResponse({'success': False, 'error': 'Неверная цена'})


@login_required
def my_price_offers(request):
    """Мои предложения цен"""
    # Сделанные предложения
    offers_made = PriceOffer.objects.filter(
        buyer=request.user
    ).select_related('listing', 'seller').order_by('-created_at')
    
    # Полученные предложения
    offers_received = PriceOffer.objects.filter(
        seller=request.user
    ).select_related('listing', 'buyer').order_by('-created_at')
    
    context = {
        'offers_made': offers_made,
        'offers_received': offers_received,
    }
    return render(request, 'listings/my_price_offers.html', context)


@login_required
@require_http_methods(['POST'])
def respond_to_offer(request, offer_id):
    """Ответить на предложение цены"""
    offer = get_object_or_404(PriceOffer, id=offer_id)
    
    # Только продавец может отвечать
    if offer.seller != request.user:
        return JsonResponse({'success': False, 'error': 'У вас нет прав'})
    
    action = request.POST.get('action')
    
    if action == 'accept':
        offer.accept()
        messages.success(request, f'Предложение принято! Новая цена: {offer.offered_price} ₽')
        return JsonResponse({'success': True, 'action': 'accepted'})
    
    elif action == 'reject':
        offer.reject()
        messages.info(request, 'Предложение отклонено')
        return JsonResponse({'success': True, 'action': 'rejected'})
    
    elif action == 'counter':
        counter_price = request.POST.get('counter_price')
        counter_message = request.POST.get('counter_message', '')
        
        try:
            counter_price = Decimal(counter_price)
            offer.counter(counter_price, counter_message)
            messages.success(request, 'Встречное предложение отправлено')
            return JsonResponse({'success': True, 'action': 'countered'})
        except:
            return JsonResponse({'success': False, 'error': 'Неверная цена'})
    
    return JsonResponse({'success': False, 'error': 'Неверное действие'})


@login_required
@require_http_methods(['POST'])
def reserve_listing(request, listing_id):
    """Зарезервировать объявление"""
    listing = get_object_or_404(Listing, id=listing_id, status='active')
    
    # Нельзя резервировать свое объявление
    if listing.seller == request.user:
        return JsonResponse({'success': False, 'error': 'Нельзя резервировать свое объявление'})
    
    duration_hours = int(request.POST.get('duration_hours', 24))
    
    # Проверяем нет ли уже активного резервирования
    existing = ListingReservation.objects.filter(
        listing=listing,
        buyer=request.user,
        status='active'
    ).first()
    
    if existing and existing.is_active():
        return JsonResponse({'success': False, 'error': 'Объявление уже зарезервировано вами'})
    
    # Создаем резервирование
    reservation = ListingReservation.objects.create(
        listing=listing,
        buyer=request.user,
        duration_hours=duration_hours
    )
    
    # Меняем статус объявления
    listing.status = 'reserved'
    listing.save()
    
    # Уведомляем продавца
    from core.services import NotificationService  
    NotificationService.notify_listing_reserved(reservation)
    
    return JsonResponse({
        'success': True,
        'message': f'Объявление зарезервировано на {duration_hours} часов',
        'expires_at': reservation.expires_at.isoformat()
    })


@login_required
def my_reservations(request):
    """Мои резервирования"""
    reservations = ListingReservation.objects.filter(
        buyer=request.user
    ).select_related('listing', 'listing__seller').order_by('-created_at')
    
    context = {
        'reservations': reservations
    }
    return render(request, 'listings/my_reservations.html', context)


@login_required
@require_http_methods(['POST'])
def cancel_reservation(request, reservation_id):
    """Отменить резервирование"""
    reservation = get_object_or_404(ListingReservation, id=reservation_id)
    
    if reservation.buyer != request.user:
        return JsonResponse({'success': False, 'error': 'У вас нет прав'})
    
    reservation.cancel()
    
    return JsonResponse({'success': True, 'message': 'Резервирование отменено'})


def listing_price_history(request, listing_id):
    """История цен объявления"""
    listing = get_object_or_404(Listing, id=listing_id)
    
    price_history = PriceHistory.objects.filter(
        listing=listing
    ).order_by('-changed_at')
    
    context = {
        'listing': listing,
        'price_history': price_history
    }
    return render(request, 'listings/price_history.html', context)

