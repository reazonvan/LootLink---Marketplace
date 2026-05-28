import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from accounts.models import CustomUser
from listings.models import Listing

from .forms import MessageForm
from .models import Conversation, Message

logger = logging.getLogger(__name__)


@login_required
def conversations_list(request):
    """Список всех бесед пользователя с annotate(Count) вместо prefetch-list.

    P2-4: было `len(conversation.unread_messages)` — выгружало ВСЕ unread
    сообщения в память. Теперь — Count annotation одним запросом.
    """
    from django.db.models import Count, Prefetch
    from django.db.models import Q as QueryQ

    conversations = (
        Conversation.objects.filter(Q(participant1=request.user) | Q(participant2=request.user))
        .select_related(
            "participant1",
            "participant1__profile",
            "participant2",
            "participant2__profile",
            "listing",
            "listing__game",
        )
        .prefetch_related(
            Prefetch(
                "messages",
                queryset=Message.objects.select_related("sender").order_by("-created_at")[:1],
                to_attr="latest_messages",
            )
        )
        .annotate(
            unread_count=Count(
                "messages",
                filter=QueryQ(messages__is_read=False) & ~QueryQ(messages__sender=request.user),
            )
        )
        .order_by("-updated_at")
    )

    for conversation in conversations:
        conversation.other_user = conversation.get_other_participant(request.user)
        conversation.last_message = (
            conversation.latest_messages[0] if conversation.latest_messages else None
        )

    context = {"conversations": conversations}
    return render(request, "chat/conversations_list.html", context)


@login_required
def conversation_detail(request, pk):
    """Детальный просмотр беседы с возможностью отправки сообщений.

    P1-21: загружаем только последние MESSAGES_PAGE_SIZE сообщений.
    Старые подтягиваются через AJAX endpoint (get_new_messages с параметром
    before_id, можно реализовать симметрично).
    """
    MESSAGES_PAGE_SIZE = 100

    conversation = get_object_or_404(Conversation, pk=pk)

    if request.user not in [conversation.participant1, conversation.participant2]:
        logger.warning(
            "chat IDOR attempt on conversation_detail: user=%s conv=%s",
            request.user.pk,
            conversation.pk,
        )
        messages.error(request, "У вас нет доступа к этой беседе.")
        return redirect("chat:conversations_list")

    # Отмечаем как прочитанные одним запросом
    Message.objects.filter(conversation=conversation, is_read=False).exclude(
        sender=request.user
    ).update(is_read=True)

    # Загружаем последние N сообщений. desc → reverse в шаблоне.
    messages_qs = conversation.messages.select_related("sender", "sender__profile").order_by(
        "-created_at"
    )[:MESSAGES_PAGE_SIZE]
    messages_list = list(reversed(list(messages_qs)))

    # Обработка отправки сообщения
    if request.method == "POST":
        form = MessageForm(request.POST, request.FILES)
        if form.is_valid():
            message = form.save(commit=False)
            message.conversation = conversation
            message.sender = request.user
            message.save()
            logger.info(
                "chat message via form: id=%s conv=%s sender=%s has_image=%s",
                message.pk,
                conversation.pk,
                request.user.pk,
                bool(message.image),
            )

            # Обновляем last_seen отправителя сразу
            from django.utils import timezone

            from accounts.models import Profile

            Profile.objects.filter(user=request.user).update(last_seen=timezone.now())

            # Если AJAX запрос, возвращаем JSON
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                image_url = message.image.url if message.image else None
                return JsonResponse(
                    {
                        "success": True,
                        "message": {
                            "id": message.id,
                            "content": message.content,
                            "sender_id": message.sender.id,
                            "sender_username": message.sender.username,
                            "created_at": message.created_at.isoformat(),
                            "is_read": False,
                            "image_url": image_url,
                        },
                    }
                )

            return redirect("chat:conversation_detail", pk=pk)
    else:
        form = MessageForm()

    other_user = conversation.get_other_participant(request.user)

    context = {
        "conversation": conversation,
        "chat_messages": messages_list,
        "form": form,
        "other_user": other_user,
    }

    return render(request, "chat/conversation_detail.html", context)


@login_required
def conversation_start(request, listing_pk):
    """Начать беседу по объявлению с защитой от дублирования."""
    from django.db import IntegrityError, transaction

    listing = get_object_or_404(Listing, pk=listing_pk)

    # Нельзя начать беседу с самим собой
    if listing.seller == request.user:
        logger.info(
            "chat start blocked (self-listing): user=%s listing=%s",
            request.user.pk,
            listing.pk,
        )
        messages.error(request, "Вы не можете начать беседу по своему объявлению.")
        return redirect("listings:listing_detail", pk=listing_pk)

    # Используем правильную сортировку участников для консистентности
    participant1, participant2 = sorted([request.user, listing.seller], key=lambda u: u.pk)

    # Используем get_or_create с транзакцией для атомарности
    created = False
    try:
        with transaction.atomic():
            conversation, created = Conversation.objects.get_or_create(
                participant1=participant1,
                participant2=participant2,
                listing=listing,
                defaults={
                    "participant1": participant1,
                    "participant2": participant2,
                    "listing": listing,
                },
            )

            # Беседа создана — контекст товара показывается как карточка в чате
    except IntegrityError:
        # На случай если все равно создался дубликат (крайне редко)
        logger.warning(
            "chat start IntegrityError fallback: buyer=%s seller=%s listing=%s",
            request.user.pk,
            listing.seller_id,
            listing.pk,
        )
        conversation = Conversation.objects.filter(
            Q(participant1=participant1, participant2=participant2, listing=listing)
            | Q(participant1=participant2, participant2=participant1, listing=listing)
        ).first()

    if created:
        logger.info(
            "chat conversation started: id=%s buyer=%s seller=%s listing=%s",
            conversation.pk,
            request.user.pk,
            listing.seller_id,
            listing.pk,
        )
    return redirect("chat:conversation_detail", pk=conversation.pk)


@login_required
@require_http_methods(["GET"])
def get_new_messages(request, conversation_pk):
    """API endpoint для получения новых сообщений (AJAX)."""
    from django.core.cache import cache

    # Rate limiting: 200 запросов в минуту на пользователя (для polling каждые 3 секунды)
    cache_key = f"chat_poll_rate_{request.user.id}_{conversation_pk}"
    requests_count = cache.get(cache_key, 0)

    if requests_count >= 200:
        logger.warning(
            "chat poll rate-limited: user=%s conv=%s count=%s",
            request.user.pk,
            conversation_pk,
            requests_count,
        )
        return JsonResponse(
            {"error": "Слишком много запросов. Подождите минуту.", "messages": []}, status=429
        )

    cache.set(cache_key, requests_count + 1, 60)

    conversation = get_object_or_404(Conversation, pk=conversation_pk)

    # Проверяем доступ
    if request.user not in [conversation.participant1, conversation.participant2]:
        logger.warning(
            "chat IDOR attempt on get_new_messages: user=%s conv=%s",
            request.user.pk,
            conversation.pk,
        )
        return JsonResponse({"error": "Доступ запрещён"}, status=403)

    # P3-12: cast after в int — иначе ORM может ругнуться на «'after'» строку.
    try:
        after_id = int(request.GET.get("after", 0))
    except (TypeError, ValueError):
        after_id = 0

    new_messages = (
        conversation.messages.filter(id__gt=after_id)
        .select_related("sender")
        .order_by("created_at")[:100]
    )

    messages_data = []
    for message in new_messages:
        messages_data.append(
            {
                "id": message.id,
                "content": message.content,
                "sender_id": message.sender.id,
                "sender_username": message.sender.username,
                "created_at": message.created_at.isoformat(),
                "is_read": message.is_read,
                "image_url": message.image.url if message.image else None,
            }
        )

    return JsonResponse({"messages": messages_data, "count": len(messages_data)})
