from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from accounts.models import CustomUser
from listings.models import Listing
from .models import Conversation, Message
from .forms import MessageForm


@login_required
def conversations_list(request):
    """Список всех бесед пользователя с оптимизацией N+1 запросов."""
    from django.db.models import Prefetch, Count, Q as QueryQ
    
    # Оптимизация: загружаем последнее сообщение и подсчитываем непрочитанные за 1 запрос
    conversations = Conversation.objects.filter(
        Q(participant1=request.user) | Q(participant2=request.user)
    ).select_related(
        'participant1', 'participant1__profile',
        'participant2', 'participant2__profile',
        'listing', 'listing__game'
    ).prefetch_related(
        # Prefetch последнего сообщения (самое новое)
        Prefetch(
            'messages',
            queryset=Message.objects.select_related('sender').order_by('-created_at')[:1],
            to_attr='latest_messages'
        ),
        # Prefetch всех сообщений для подсчета непрочитанных
        Prefetch(
            'messages',
            queryset=Message.objects.filter(~QueryQ(sender=request.user), is_read=False),
            to_attr='unread_messages'
        )
    ).order_by('-updated_at')
    
    # Теперь добавляем вычисляемые поля без дополнительных запросов
    for conversation in conversations:
        # Количество непрочитанных уже загружено через prefetch
        conversation.unread_count = len(conversation.unread_messages)
        # Другой участник
        conversation.other_user = conversation.get_other_participant(request.user)
        # Последнее сообщение уже загружено через prefetch
        conversation.last_message = conversation.latest_messages[0] if conversation.latest_messages else None
    
    context = {
        'conversations': conversations,
    }
    
    return render(request, 'chat/conversations_list.html', context)


@login_required
def conversation_detail(request, pk):
    """Детальный просмотр беседы с возможностью отправки сообщений."""
    conversation = get_object_or_404(Conversation, pk=pk)
    
    # Проверяем, является ли пользователь участником беседы
    if request.user not in [conversation.participant1, conversation.participant2]:
        messages.error(request, 'У вас нет доступа к этой беседе.')
        return redirect('chat:conversations_list')
    
    # Отмечаем все сообщения как прочитанные
    Message.objects.filter(
        conversation=conversation,
        is_read=False
    ).exclude(sender=request.user).update(is_read=True)
    
    # Получаем сообщения
    messages_list = conversation.messages.select_related('sender').order_by('created_at')
    
    # Обработка отправки сообщения
    if request.method == 'POST':
        form = MessageForm(request.POST)
        if form.is_valid():
            message = form.save(commit=False)
            message.conversation = conversation
            message.sender = request.user
            message.save()
            
            # Обновляем last_seen отправителя сразу
            from django.utils import timezone
            from accounts.models import Profile
            Profile.objects.filter(user=request.user).update(last_seen=timezone.now())
            
            # Если AJAX запрос, возвращаем JSON
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': {
                        'id': message.id,
                        'content': message.content,
                        'sender': message.sender.username,
                        'is_own': True,
                        'created_at': message.created_at.strftime('%H:%M'),
                    }
                })
            
            return redirect('chat:conversation_detail', pk=pk)
    else:
        form = MessageForm()
    
    other_user = conversation.get_other_participant(request.user)
    
    context = {
        'conversation': conversation,
        'messages': messages_list,
        'form': form,
        'other_user': other_user,
    }
    
    return render(request, 'chat/conversation_detail.html', context)


@login_required
def conversation_start(request, listing_pk):
    """Начать беседу по объявлению с защитой от дублирования."""
    from django.db import transaction, IntegrityError
    
    listing = get_object_or_404(Listing, pk=listing_pk)
    
    # Нельзя начать беседу с самим собой
    if listing.seller == request.user:
        messages.error(request, 'Вы не можете начать беседу по своему объявлению.')
        return redirect('listings:listing_detail', pk=listing_pk)
    
    # Используем правильную сортировку участников для консистентности
    participant1, participant2 = sorted([request.user, listing.seller], key=lambda u: u.pk)
    
    # Используем get_or_create с транзакцией для атомарности
    try:
        with transaction.atomic():
            conversation, created = Conversation.objects.get_or_create(
                participant1=participant1,
                participant2=participant2,
                listing=listing,
                defaults={
                    'participant1': participant1,
                    'participant2': participant2,
                    'listing': listing
                }
            )
            
            # Если беседа только что создана - создаем приветственное сообщение
            if created:
                Message.objects.create(
                    conversation=conversation,
                    sender=request.user,
                    content=f'Здравствуйте! Интересует товар: {listing.title}'
                )
    except IntegrityError:
        # На случай если все равно создался дубликат (крайне редко)
        conversation = Conversation.objects.filter(
            Q(participant1=participant1, participant2=participant2, listing=listing) |
            Q(participant1=participant2, participant2=participant1, listing=listing)
        ).first()
    
    return redirect('chat:conversation_detail', pk=conversation.pk)


@login_required
@require_http_methods(["GET"])
def get_new_messages(request, conversation_pk):
    """API endpoint для получения новых сообщений (AJAX)."""
    from django.core.cache import cache
    
    # Rate limiting: 200 запросов в минуту на пользователя (для polling каждые 3 секунды)
    cache_key = f'chat_poll_rate_{request.user.id}_{conversation_pk}'
    requests_count = cache.get(cache_key, 0)
    
    if requests_count >= 200:
        return JsonResponse({
            'error': 'Слишком много запросов. Подождите минуту.',
            'messages': []
        }, status=429)
    
    cache.set(cache_key, requests_count + 1, 60)
    
    conversation = get_object_or_404(Conversation, pk=conversation_pk)
    
    # Проверяем доступ
    if request.user not in [conversation.participant1, conversation.participant2]:
        return JsonResponse({'error': 'Доступ запрещён'}, status=403)
    
    # Получаем ID последнего сообщения
    after_id = request.GET.get('after', 0)
    
    # Загружаем новые сообщения с оптимизацией
    new_messages = conversation.messages.filter(
        id__gt=after_id
    ).select_related('sender').order_by('created_at')
    
    messages_data = []
    for message in new_messages:
        messages_data.append({
            'id': message.id,
            'content': message.content,
            'sender': message.sender.username,
            'is_own': message.sender == request.user,
            'created_at': message.created_at.strftime('%H:%M'),
        })
    
    return JsonResponse({
        'messages': messages_data,
        'count': len(messages_data)
    })

