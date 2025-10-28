from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from listings.models import Listing
from .models import PurchaseRequest, Review
from .forms import PurchaseRequestForm, ReviewForm


@login_required
def purchase_request_create(request, listing_pk):
    """Создание запроса на покупку."""
    listing = get_object_or_404(Listing, pk=listing_pk)
    
    # Проверки
    if listing.seller == request.user:
        messages.error(request, 'Вы не можете купить свое собственное объявление.')
        return redirect('listings:listing_detail', pk=listing_pk)
    
    if not listing.is_available():
        messages.error(request, 'Это объявление больше не доступно.')
        return redirect('listings:listing_detail', pk=listing_pk)
    
    # Проверяем, нет ли уже активного запроса
    existing_request = PurchaseRequest.objects.filter(
        listing=listing,
        buyer=request.user,
        status__in=['pending', 'accepted']
    ).first()
    
    if existing_request:
        messages.info(request, 'У вас уже есть активный запрос на это объявление.')
        return redirect('transactions:purchase_request_detail', pk=existing_request.pk)
    
    if request.method == 'POST':
        form = PurchaseRequestForm(request.POST)
        if form.is_valid():
            purchase_request = form.save(commit=False)
            purchase_request.listing = listing
            purchase_request.buyer = request.user
            purchase_request.seller = listing.seller
            purchase_request.save()
            
            # Создаем уведомление для продавца через NotificationService
            from core.services import NotificationService
            NotificationService.notify_purchase_request(purchase_request)
            
            messages.success(request, 'Запрос на покупку отправлен!')
            return redirect('transactions:purchase_request_detail', pk=purchase_request.pk)
    else:
        form = PurchaseRequestForm()
    
    context = {
        'form': form,
        'listing': listing,
    }
    
    return render(request, 'transactions/purchase_request_create.html', context)


@login_required
def purchase_request_detail(request, pk):
    """Детальная информация о запросе на покупку."""
    purchase_request = get_object_or_404(
        PurchaseRequest.objects.select_related('listing', 'buyer', 'seller'),
        pk=pk
    )
    
    # Доступ только для участников сделки
    if request.user not in [purchase_request.buyer, purchase_request.seller]:
        messages.error(request, 'У вас нет доступа к этой странице.')
        return redirect('listings:home')
    
    # Проверяем, может ли пользователь оставить отзыв
    can_leave_review = (
        purchase_request.status == 'completed' and
        not Review.objects.filter(
            purchase_request=purchase_request,
            reviewer=request.user
        ).exists()
    )
    
    context = {
        'purchase_request': purchase_request,
        'can_leave_review': can_leave_review,
    }
    
    return render(request, 'transactions/purchase_request_detail.html', context)


@login_required
def purchase_request_accept(request, pk):
    """Принятие запроса на покупку (для продавца)."""
    purchase_request = get_object_or_404(PurchaseRequest, pk=pk, seller=request.user)
    
    if purchase_request.status != 'pending':
        messages.error(request, 'Этот запрос уже обработан.')
        return redirect('transactions:purchase_request_detail', pk=pk)
    
    if request.method == 'POST':
        purchase_request.accept()
        
        # Создаем уведомление для покупателя через NotificationService
        from core.services import NotificationService
        NotificationService.notify_request_accepted(purchase_request)
        
        messages.success(request, 'Запрос принят! Свяжитесь с покупателем для завершения сделки.')
        return redirect('transactions:purchase_request_detail', pk=pk)
    
    return render(request, 'transactions/purchase_request_accept.html', {
        'purchase_request': purchase_request
    })


@login_required
def purchase_request_reject(request, pk):
    """Отклонение запроса на покупку (для продавца)."""
    purchase_request = get_object_or_404(PurchaseRequest, pk=pk, seller=request.user)
    
    if purchase_request.status != 'pending':
        messages.error(request, 'Этот запрос уже обработан.')
        return redirect('transactions:purchase_request_detail', pk=pk)
    
    if request.method == 'POST':
        purchase_request.reject()
        
        # Создаем уведомление для покупателя через NotificationService
        from core.services import NotificationService
        NotificationService.notify_request_rejected(purchase_request)
        
        messages.info(request, 'Запрос отклонен.')
        return redirect('accounts:my_sales')
    
    return render(request, 'transactions/purchase_request_reject.html', {
        'purchase_request': purchase_request
    })


@login_required
def purchase_request_complete(request, pk):
    """Завершение сделки (для продавца)."""
    purchase_request = get_object_or_404(PurchaseRequest, pk=pk, seller=request.user)
    
    if purchase_request.status != 'accepted':
        messages.error(request, 'Сделка должна быть сначала принята.')
        return redirect('transactions:purchase_request_detail', pk=pk)
    
    if request.method == 'POST':
        purchase_request.complete()
        
        # Создаем уведомление для покупателя через NotificationService
        from core.services import NotificationService
        NotificationService.notify_deal_completed(purchase_request)
        
        messages.success(request, 'Сделка завершена! Не забудьте оставить отзыв.')
        return redirect('transactions:purchase_request_detail', pk=pk)
    
    return render(request, 'transactions/purchase_request_complete.html', {
        'purchase_request': purchase_request
    })


@login_required
def purchase_request_cancel(request, pk):
    """Отмена запроса (для покупателя)."""
    purchase_request = get_object_or_404(PurchaseRequest, pk=pk, buyer=request.user)
    
    if purchase_request.status in ['completed', 'cancelled']:
        messages.error(request, 'Этот запрос нельзя отменить.')
        return redirect('transactions:purchase_request_detail', pk=pk)
    
    if request.method == 'POST':
        purchase_request.status = 'cancelled'
        purchase_request.save()
        
        # Если объявление было зарезервировано, возвращаем его в активные
        if purchase_request.listing.status == 'reserved':
            purchase_request.listing.status = 'active'
            purchase_request.listing.save()
        
        messages.info(request, 'Запрос отменен.')
        return redirect('accounts:my_purchases')
    
    return render(request, 'transactions/purchase_request_cancel.html', {
        'purchase_request': purchase_request
    })


@login_required
def review_create(request, purchase_request_pk):
    """Создание отзыва после завершения сделки."""
    purchase_request = get_object_or_404(PurchaseRequest, pk=purchase_request_pk)
    
    # Проверки
    if request.user not in [purchase_request.buyer, purchase_request.seller]:
        messages.error(request, 'У вас нет доступа к этой странице.')
        return redirect('listings:home')
    
    if purchase_request.status != 'completed':
        messages.error(request, 'Отзыв можно оставить только после завершения сделки.')
        return redirect('transactions:purchase_request_detail', pk=purchase_request_pk)
    
    # Проверяем, не оставлял ли уже отзыв
    if Review.objects.filter(purchase_request=purchase_request, reviewer=request.user).exists():
        messages.info(request, 'Вы уже оставили отзыв по этой сделке.')
        return redirect('transactions:purchase_request_detail', pk=purchase_request_pk)
    
    # Определяем, кого оценивает пользователь
    reviewed_user = (
        purchase_request.seller if request.user == purchase_request.buyer
        else purchase_request.buyer
    )
    
    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.purchase_request = purchase_request
            review.reviewer = request.user
            review.reviewed_user = reviewed_user
            review.save()
            
            # Создаем уведомление для оцениваемого пользователя через NotificationService
            from core.services import NotificationService
            NotificationService.notify_new_review(review)
            
            messages.success(request, 'Отзыв успешно оставлен!')
            return redirect('accounts:profile', username=reviewed_user.username)
    else:
        form = ReviewForm()
    
    context = {
        'form': form,
        'purchase_request': purchase_request,
        'reviewed_user': reviewed_user,
    }
    
    return render(request, 'transactions/review_create.html', context)

