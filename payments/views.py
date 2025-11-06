from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
from django.urls import reverse
from .models import Wallet, Transaction, Escrow, PromoCode, Withdrawal
from .forms import DepositForm, PromoCodeForm, WithdrawalForm
from .yookassa_integration import yookassa_service
import json
import logging

logger = logging.getLogger(__name__)


@login_required
def wallet_dashboard(request):
    """Дашборд кошелька пользователя"""
    wallet, created = Wallet.objects.get_or_create(user=request.user)
    
    # Последние транзакции
    transactions = Transaction.objects.filter(
        user=request.user
    ).select_related('purchase_request')[:20]
    
    # Активные эскроу
    active_escrows = Escrow.objects.filter(
        buyer=request.user,
        status='funded'
    ).select_related('seller', 'purchase_request__listing')
    
    # Ожидающие выводы
    pending_withdrawals = Withdrawal.objects.filter(
        user=request.user,
        status='pending'
    )
    
    context = {
        'wallet': wallet,
        'transactions': transactions,
        'active_escrows': active_escrows,
        'pending_withdrawals': pending_withdrawals,
    }
    return render(request, 'payments/wallet_dashboard.html', context)


@login_required
def deposit(request):
    """Пополнение баланса"""
    if request.method == 'POST':
        form = DepositForm(request.POST)
        if form.is_valid():
            amount = form.cleaned_data['final_amount']
            
            # Создаем платеж через ЮKassa
            return_url = request.build_absolute_uri(reverse('payments:deposit_success'))
            result = yookassa_service.create_payment(
                user=request.user,
                amount=amount,
                description=f'Пополнение баланса на {amount} ₽',
                return_url=return_url
            )
            
            if result.get('success'):
                # Перенаправляем на страницу оплаты
                return redirect(result['confirmation_url'])
            else:
                messages.error(request, f'Ошибка создания платежа: {result.get("error")}')
    else:
        form = DepositForm()
    
    return render(request, 'payments/deposit.html', {'form': form})


@login_required
def deposit_success(request):
    """Успешное пополнение баланса"""
    messages.success(request, 'Баланс успешно пополнен!')
    return redirect('payments:wallet_dashboard')


@login_required
def withdrawal_create(request):
    """Создание заявки на вывод средств"""
    wallet, _ = Wallet.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        form = WithdrawalForm(user=request.user, data=request.POST)
        if form.is_valid():
            withdrawal = form.save(commit=False)
            withdrawal.user = request.user
            withdrawal.save()
            
            messages.success(request, 'Заявка на вывод средств создана. Ожидайте обработки администратором.')
            return redirect('payments:wallet_dashboard')
    else:
        form = WithdrawalForm(user=request.user)
    
    context = {
        'form': form,
        'wallet': wallet,
        'available_balance': wallet.get_available_balance()
    }
    return render(request, 'payments/withdrawal_create.html', context)


@login_required
@require_http_methods(['POST'])
def apply_promo_code(request):
    """Применить промокод (AJAX)"""
    form = PromoCodeForm(request.POST)
    if form.is_valid():
        promo_code = form.promo_code
        
        # Сохраняем промокод в сессии
        request.session['promo_code'] = promo_code.code
        
        return JsonResponse({
            'success': True,
            'message': f'Промокод применен! Скидка: {promo_code.discount_value}{"%" if promo_code.discount_type == "percent" else "₽"}',
            'discount_type': promo_code.discount_type,
            'discount_value': float(promo_code.discount_value)
        })
    else:
        return JsonResponse({
            'success': False,
            'errors': form.errors
        }, status=400)


@csrf_exempt
@require_http_methods(['POST'])
def yookassa_webhook(request):
    """
    Webhook для получения уведомлений от ЮKassa.
    Важно: не забудьте настроить webhook в личном кабинете ЮKassa.
    """
    try:
        webhook_data = json.loads(request.body)
        logger.info(f'Получен webhook от ЮKassa: {webhook_data}')
        
        success = yookassa_service.handle_webhook(webhook_data)
        
        if success:
            return HttpResponse(status=200)
        else:
            return HttpResponse(status=400)
            
    except Exception as e:
        logger.error(f'Ошибка обработки webhook: {str(e)}')
        return HttpResponse(status=500)


@login_required
def transaction_history(request):
    """История транзакций"""
    transactions = Transaction.objects.filter(
        user=request.user
    ).select_related('purchase_request__listing').order_by('-created_at')
    
    # Фильтрация по типу
    transaction_type = request.GET.get('type')
    if transaction_type:
        transactions = transactions.filter(transaction_type=transaction_type)
    
    # Фильтрация по статусу
    status = request.GET.get('status')
    if status:
        transactions = transactions.filter(status=status)
    
    context = {
        'transactions': transactions,
        'transaction_types': Transaction.TRANSACTION_TYPES,
        'statuses': Transaction.STATUS_CHOICES,
    }
    return render(request, 'payments/transaction_history.html', context)


@login_required
def escrow_detail(request, escrow_id):
    """Детали эскроу"""
    escrow = get_object_or_404(Escrow, id=escrow_id)
    
    # Проверка прав доступа
    if request.user != escrow.buyer and request.user != escrow.seller:
        messages.error(request, 'У вас нет доступа к этому эскроу')
        return redirect('payments:wallet_dashboard')
    
    return render(request, 'payments/escrow_detail.html', {'escrow': escrow})

