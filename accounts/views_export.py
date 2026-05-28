"""
Views для экспорта пользовательских данных (GDPR compliance).
"""

import json
import os
import zipfile
from datetime import timedelta
from io import BytesIO

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import models
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone


@login_required
def request_data_export(request):
    """
    Страница запроса экспорта данных.
    """
    from accounts.models_export import DataExportRequest

    # Проверяем есть ли активный запрос
    active_request = DataExportRequest.objects.filter(
        user=request.user, status__in=["pending", "processing"]
    ).first()

    # Получаем завершенные запросы (последние 5)
    completed_requests = DataExportRequest.objects.filter(
        user=request.user, status="completed", expires_at__gt=timezone.now()  # Только не истекшие
    ).order_by("-created_at")[:5]

    if request.method == "POST":
        if active_request:
            messages.warning(request, "У вас уже есть активный запрос на экспорт данных.")
            return redirect("accounts:data_export")

        # Создаем новый запрос
        export_request = DataExportRequest.objects.create(user=request.user)

        # Запускаем задачу Celery.
        # Phase 13: откладываем .delay() до коммита — иначе worker может
        # не найти DataExportRequest, если транзакция ещё не закоммичена.
        from django.db import transaction as db_transaction

        from accounts.tasks_export import generate_data_export

        export_id = export_request.id
        db_transaction.on_commit(lambda: generate_data_export.delay(export_id))

        messages.success(
            request, "Запрос на экспорт данных создан. Вы получите email когда файл будет готов."
        )
        return redirect("accounts:data_export")

    context = {
        "active_request": active_request,
        "completed_requests": completed_requests,
    }
    return render(request, "accounts/data_export.html", context)


@login_required
def download_data_export(request, export_id):
    """
    Скачивание файла экспорта.
    """
    from accounts.models_export import DataExportRequest

    try:
        export_request = DataExportRequest.objects.get(
            id=export_id, user=request.user, status="completed"
        )
    except DataExportRequest.DoesNotExist:
        raise Http404("Экспорт не найден")

    # Проверяем что файл существует
    if not export_request.file_path or not os.path.exists(export_request.file_path):
        messages.error(request, "Файл экспорта не найден или был удален.")
        return redirect("accounts:data_export")

    # Проверяем срок действия (7 дней)
    if export_request.expires_at and timezone.now() > export_request.expires_at:
        messages.error(request, "Срок действия ссылки истек. Создайте новый запрос.")
        return redirect("accounts:data_export")

    # Отдаем файл
    response = FileResponse(
        open(export_request.file_path, "rb"),
        as_attachment=True,
        filename=f'lootlink_data_{request.user.username}_{export_request.created_at.strftime("%Y%m%d")}.zip',
    )

    return response


def generate_export_data(user):
    """
    Генерирует JSON с данными пользователя.
    """
    from chat.models import Conversation, Message
    from listings.models import Favorite, Listing
    from transactions.models import PurchaseRequest, Review

    data = {
        "export_date": timezone.now().isoformat(),
        "user": {
            "username": user.username,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "date_joined": user.date_joined.isoformat(),
        },
        "profile": {
            "bio": user.profile.bio,
            "phone": user.profile.phone,
            "rating": float(user.profile.rating),
            "total_sales": user.profile.total_sales,
            "total_purchases": user.profile.total_purchases,
            "is_verified": user.profile.is_verified,
        },
        "listings": [],
        "favorites": [],
        "purchases": [],
        "sales": [],
        "reviews_given": [],
        "reviews_received": [],
        "messages": [],
    }

    # A2: iterator() — экспорт у power-user'а с 10k+ записями не должен
    # грузить всё в память сразу. chunk_size=500 для баланса памяти/IO.
    # Полный фикс — streaming JSON через Celery + upload в S3.
    CHUNK = 500

    # Объявления
    listings_qs = Listing.objects.filter(seller=user).select_related("game")
    for listing in listings_qs.iterator(chunk_size=CHUNK):
        data["listings"].append(
            {
                "title": listing.title,
                "description": listing.description,
                "price": float(listing.price),
                "game": listing.game.name,
                "status": listing.status,
                "created_at": listing.created_at.isoformat(),
            }
        )

    # Избранное
    favs_qs = Favorite.objects.filter(user=user).select_related("listing")
    for fav in favs_qs.iterator(chunk_size=CHUNK):
        data["favorites"].append(
            {
                "listing_title": fav.listing.title,
                "added_at": fav.created_at.isoformat(),
            }
        )

    # Покупки
    purchases_qs = PurchaseRequest.objects.filter(buyer=user).select_related("listing", "seller")
    for purchase in purchases_qs.iterator(chunk_size=CHUNK):
        data["purchases"].append(
            {
                "listing": purchase.listing.title,
                "seller": purchase.seller.username,
                "status": purchase.status,
                "created_at": purchase.created_at.isoformat(),
            }
        )

    # Продажи
    sales_qs = PurchaseRequest.objects.filter(seller=user).select_related("listing", "buyer")
    for sale in sales_qs.iterator(chunk_size=CHUNK):
        data["sales"].append(
            {
                "listing": sale.listing.title,
                "buyer": sale.buyer.username,
                "status": sale.status,
                "created_at": sale.created_at.isoformat(),
            }
        )

    # Отзывы (данные)
    reviews_given_qs = Review.objects.filter(reviewer=user).select_related("reviewed_user")
    for review in reviews_given_qs.iterator(chunk_size=CHUNK):
        data["reviews_given"].append(
            {
                "reviewed_user": review.reviewed_user.username,
                "rating": review.rating,
                "comment": review.comment,
                "created_at": review.created_at.isoformat(),
            }
        )

    reviews_received_qs = Review.objects.filter(reviewed_user=user).select_related("reviewer")
    for review in reviews_received_qs.iterator(chunk_size=CHUNK):
        data["reviews_received"].append(
            {
                "reviewer": review.reviewer.username,
                "rating": review.rating,
                "comment": review.comment,
                "created_at": review.created_at.isoformat(),
            }
        )

    # Сообщения
    conversations = Conversation.objects.filter(
        models.Q(participant1=user) | models.Q(participant2=user)
    )

    for conv in conversations:
        other_user = conv.get_other_participant(user)
        messages = Message.objects.filter(conversation=conv).order_by("created_at")

        conv_data = {"with_user": other_user.username, "messages": []}

        for msg in messages:
            conv_data["messages"].append(
                {
                    "sender": msg.sender.username,
                    "content": msg.content,
                    "created_at": msg.created_at.isoformat(),
                }
            )

        data["messages"].append(conv_data)

    return data
