"""
Views для работы со спорами.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from .models import PurchaseRequest
from .models_disputes import Dispute, DisputeMessage, DisputeEvidence
from django import forms


class DisputeForm(forms.ModelForm):
    """Форма создания спора"""
    class Meta:
        model = Dispute
        fields = ['reason', 'description']
        widgets = {
            'reason': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Подробно опишите проблему...'
            })
        }


class DisputeMessageForm(forms.ModelForm):
    """Форма отправки сообщения в споре"""
    class Meta:
        model = DisputeMessage
        fields = ['message']
        widgets = {
            'message': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Введите сообщение...'
            })
        }


@login_required
def create_dispute(request, purchase_request_id):
    """Создание спора по сделке"""
    purchase_request = get_object_or_404(PurchaseRequest, id=purchase_request_id)
    
    # Проверка прав
    if request.user != purchase_request.buyer and request.user != purchase_request.seller:
        messages.error(request, 'У вас нет доступа к этой сделке')
        return redirect('listings:home')
    
    # Проверка что спор еще не создан
    if hasattr(purchase_request, 'dispute'):
        messages.info(request, 'Спор по этой сделке уже существует')
        return redirect('transactions:dispute_detail', dispute_id=purchase_request.dispute.id)
    
    # Проверка что сделка в нужном статусе
    if purchase_request.status not in ['accepted', 'completed']:
        messages.error(request, 'Спор можно открыть только для принятых или завершенных сделок')
        return redirect('transactions:purchase_request_detail', pk=purchase_request_id)
    
    if request.method == 'POST':
        form = DisputeForm(request.POST)
        if form.is_valid():
            dispute = form.save(commit=False)
            dispute.purchase_request = purchase_request
            dispute.initiator = request.user
            dispute.save()
            
            messages.success(request, 'Спор создан. Модератор рассмотрит вашу жалобу в ближайшее время.')
            return redirect('transactions:dispute_detail', dispute_id=dispute.id)
    else:
        form = DisputeForm()
    
    context = {
        'form': form,
        'purchase_request': purchase_request
    }
    return render(request, 'transactions/dispute_create.html', context)


@login_required
def dispute_detail(request, dispute_id):
    """Детали спора"""
    dispute = get_object_or_404(Dispute, id=dispute_id)
    
    # Проверка прав доступа
    if request.user not in [dispute.initiator, dispute.purchase_request.buyer, 
                            dispute.purchase_request.seller, dispute.moderator]:
        if not request.user.is_staff:
            messages.error(request, 'У вас нет доступа к этому спору')
            return redirect('listings:home')
    
    # Обработка отправки сообщения
    if request.method == 'POST':
        form = DisputeMessageForm(request.POST)
        if form.is_valid():
            msg = form.save(commit=False)
            msg.dispute = dispute
            msg.sender = request.user
            msg.is_moderator_message = request.user.is_staff or request.user == dispute.moderator
            msg.save()
            
            messages.success(request, 'Сообщение отправлено')
            return redirect('transactions:dispute_detail', dispute_id=dispute_id)
    else:
        form = DisputeMessageForm()
    
    messages_list = dispute.messages.select_related('sender').all()
    evidence = dispute.evidence.select_related('uploader').all()
    
    context = {
        'dispute': dispute,
        'messages_list': messages_list,
        'evidence': evidence,
        'form': form
    }
    return render(request, 'transactions/dispute_detail.html', context)


@login_required
def my_disputes(request):
    """Список споров пользователя"""
    # Споры где пользователь - инициатор, покупатель или продавец
    disputes = Dispute.objects.filter(
        models.Q(initiator=request.user) |
        models.Q(purchase_request__buyer=request.user) |
        models.Q(purchase_request__seller=request.user)
    ).select_related('purchase_request', 'initiator', 'moderator').order_by('-created_at')
    
    context = {
        'disputes': disputes
    }
    return render(request, 'transactions/my_disputes.html', context)


@login_required
def upload_evidence(request, dispute_id):
    """Загрузка доказательств"""
    dispute = get_object_or_404(Dispute, id=dispute_id)
    
    # Проверка прав
    if request.user not in [dispute.purchase_request.buyer, dispute.purchase_request.seller]:
        messages.error(request, 'У вас нет прав на загрузку доказательств')
        return redirect('transactions:dispute_detail', dispute_id=dispute_id)
    
    if request.method == 'POST' and request.FILES.get('file'):
        evidence = DisputeEvidence.objects.create(
            dispute=dispute,
            uploader=request.user,
            file=request.FILES['file'],
            description=request.POST.get('description', '')
        )
        messages.success(request, 'Доказательство загружено')
    
    return redirect('transactions:dispute_detail', dispute_id=dispute_id)

