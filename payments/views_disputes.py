"""
Views для системы диспутов escrow сделок.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from django.db import transaction
from .models import Escrow
from .models_disputes import Dispute, DisputeMessage, DisputeEvidence
from core.models_audit import SecurityAuditLog


def is_moderator(user):
    """Проверка что пользователь - модератор."""
    return user.is_staff or (hasattr(user, 'profile') and user.profile.is_moderator)


@login_required
def create_dispute(request, escrow_id):
    """
    Создание диспута по escrow сделке.
    Доступно только участникам сделки.
    """
    escrow = get_object_or_404(
        Escrow.objects.select_related('buyer', 'seller', 'purchase_request'),
        id=escrow_id
    )
    
    # Проверка прав доступа
    if request.user not in [escrow.buyer, escrow.seller]:
        messages.error(request, 'У вас нет доступа к этой сделке.')
        return redirect('payments:wallet_dashboard')
    
    # Проверка что escrow в статусе funded
    if escrow.status != 'funded':
        messages.error(request, 'Можно открыть диспут только для активных escrow сделок.')
        return redirect('payments:wallet_dashboard')
    
    # Проверка что диспут еще не создан
    if hasattr(escrow, 'dispute'):
        messages.info(request, 'Диспут уже существует для этой сделки.')
        return redirect('payments:dispute_detail', dispute_id=escrow.dispute.id)
    
    if request.method == 'POST':
        reason = request.POST.get('reason')
        description = request.POST.get('description', '').strip()
        
        if not description or len(description) < 20:
            messages.error(request, 'Опишите проблему детально (минимум 20 символов).')
            return render(request, 'payments/dispute_create.html', {
                'escrow': escrow,
                'reason_choices': Dispute.REASON_CHOICES
            })
        
        with transaction.atomic():
            # Создаем диспут
            dispute = Dispute.objects.create(
                escrow=escrow,
                opened_by=request.user,
                reason=reason,
                description=description,
                status='open'
            )
            
            # Обновляем статус escrow
            escrow.status = 'disputed'
            escrow.save(update_fields=['status'])
            
            # Логируем в audit
            SecurityAuditLog.log(
                action_type='suspicious_activity',
                user=request.user,
                description=f'Открыт диспут #{dispute.id} для escrow #{escrow.id}',
                risk_level='high',
                request=request,
                metadata={
                    'dispute_id': dispute.id,
                    'escrow_id': escrow.id,
                    'reason': reason
                }
            )
            
            messages.success(request, 'Диспут создан. Модератор рассмотрит его в ближайшее время.')
            return redirect('payments:dispute_detail', dispute_id=dispute.id)
    
    context = {
        'escrow': escrow,
        'reason_choices': Dispute.REASON_CHOICES
    }
    
    return render(request, 'payments/dispute_create.html', context)


@login_required
def dispute_detail(request, dispute_id):
    """
    Детальная информация о диспуте.
    Доступна участникам сделки и модераторам.
    """
    dispute = get_object_or_404(
        Dispute.objects.select_related(
            'escrow', 'escrow__buyer', 'escrow__seller',
            'opened_by', 'assigned_to'
        ),
        id=dispute_id
    )
    
    # Проверка прав доступа
    is_participant = request.user in [dispute.escrow.buyer, dispute.escrow.seller]
    is_moderator_user = is_moderator(request.user)
    
    if not (is_participant or is_moderator_user):
        messages.error(request, 'У вас нет доступа к этому диспуту.')
        return redirect('payments:wallet_dashboard')
    
    # Получаем сообщения
    dispute_messages = dispute.messages.select_related('sender').order_by('created_at')
    
    # Получаем доказательства
    evidences = dispute.evidences.select_related('uploaded_by').order_by('created_at')
    
    context = {
        'dispute': dispute,
        'messages': dispute_messages,
        'evidences': evidences,
        'is_moderator': is_moderator_user,
    }
    
    return render(request, 'payments/dispute_detail.html', context)


@login_required
def add_dispute_message(request, dispute_id):
    """Добавление сообщения в диспут."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST allowed'}, status=405)
    
    dispute = get_object_or_404(Dispute, id=dispute_id)
    
    # Проверка прав доступа
    is_participant = request.user in [dispute.escrow.buyer, dispute.escrow.seller]
    is_moderator_user = is_moderator(request.user)
    
    if not (is_participant or is_moderator_user):
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    message_text = request.POST.get('message', '').strip()
    
    if not message_text:
        return JsonResponse({'error': 'Message cannot be empty'}, status=400)
    
    # Создаем сообщение
    dispute_message = DisputeMessage.objects.create(
        dispute=dispute,
        sender=request.user,
        message=message_text,
        is_moderator_message=is_moderator_user
    )
    
    return JsonResponse({
        'success': True,
        'message': {
            'id': dispute_message.id,
            'sender': request.user.username,
            'message': message_text,
            'is_moderator': is_moderator_user,
            'created_at': dispute_message.created_at.strftime('%Y-%m-%d %H:%M')
        }
    })


@user_passes_test(is_moderator)
def moderate_dispute(request, dispute_id):
    """
    Модерация диспута.
    Доступно только модераторам.
    """
    dispute = get_object_or_404(
        Dispute.objects.select_related('escrow', 'escrow__buyer', 'escrow__seller'),
        id=dispute_id
    )
    
    if request.method == 'POST':
        action = request.POST.get('action')
        decision = request.POST.get('decision', '').strip()
        
        if not decision:
            messages.error(request, 'Необходимо указать решение.')
            return redirect('payments:dispute_detail', dispute_id=dispute_id)
        
        try:
            if action == 'resolve_buyer':
                # Решение в пользу покупателя
                dispute.resolve_for_buyer(decision, full_refund=True)
                messages.success(request, 'Диспут решен в пользу покупателя. Средства возвращены.')
                
            elif action == 'resolve_seller':
                # Решение в пользу продавца
                dispute.resolve_for_seller(decision)
                messages.success(request, 'Диспут решен в пользу продавца. Средства переведены.')
                
            elif action == 'resolve_partial':
                # Частичное решение
                refund_amount = request.POST.get('refund_amount')
                if refund_amount:
                    dispute.refund_amount = refund_amount
                    dispute.status = 'resolved_partial'
                    dispute.moderator_decision = decision
                    dispute.resolved_at = timezone.now()
                    dispute.save()
                    messages.success(request, 'Диспут решен частично.')
                else:
                    messages.error(request, 'Укажите сумму возврата.')
                    return redirect('payments:dispute_detail', dispute_id=dispute_id)
            
            elif action == 'close':
                # Закрыть без изменений
                dispute.status = 'closed'
                dispute.moderator_decision = decision
                dispute.resolved_at = timezone.now()
                dispute.save()
                messages.info(request, 'Диспут закрыт.')
            
            return redirect('payments:dispute_detail', dispute_id=dispute_id)
            
        except Exception as e:
            messages.error(request, f'Ошибка при обработке диспута: {str(e)}')
            return redirect('payments:dispute_detail', dispute_id=dispute_id)
    
    return redirect('payments:dispute_detail', dispute_id=dispute_id)


@user_passes_test(is_moderator)
def disputes_list(request):
    """
    Список всех диспутов для модераторов.
    """
    status_filter = request.GET.get('status', 'open')
    
    disputes = Dispute.objects.filter(
        status=status_filter
    ).select_related(
        'escrow', 'escrow__buyer', 'escrow__seller',
        'opened_by', 'assigned_to'
    ).order_by('-created_at')
    
    context = {
        'disputes': disputes,
        'status_filter': status_filter,
        'status_choices': Dispute.STATUS_CHOICES,
    }
    
    return render(request, 'payments/disputes_list.html', context)

