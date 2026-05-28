"""
Дашборд аналитики для продавцов и покупателей.
"""

import csv
import json
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, Q, Sum
from django.db.models.functions import TruncDate
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone

from listings.models import Listing
from transactions.models import PurchaseRequest, Review


def _parse_period(value, default=30):
    try:
        days = int(value)
    except (TypeError, ValueError):
        return default
    return max(1, min(days, 365))


@login_required
def analytics_dashboard(request):
    """Дашборд аналитики пользователя — собран в минимальное число запросов."""
    user = request.user
    period = request.GET.get("period", "30")
    days = _parse_period(period)
    start_date = timezone.now() - timedelta(days=days)

    # Один aggregate на все продажи + revenue за период.
    sales_agg = PurchaseRequest.objects.filter(seller=user).aggregate(
        total_sales=Count("id", filter=Q(status="completed")),
        total_revenue=Sum(
            "listing__price",
            filter=Q(status="completed", completed_at__gte=start_date),
        ),
    )
    listings_agg = Listing.objects.filter(seller=user).aggregate(
        avg_price=Avg("price", filter=Q(status__in=["active", "sold"])),
        active_listings=Count("id", filter=Q(status="active")),
    )
    sales_stats = {
        "total_sales": sales_agg["total_sales"] or 0,
        "total_revenue": sales_agg["total_revenue"] or Decimal("0.00"),
        "avg_price": listings_agg["avg_price"] or Decimal("0.00"),
        "active_listings": listings_agg["active_listings"] or 0,
    }

    purchase_agg = PurchaseRequest.objects.filter(buyer=user).aggregate(
        total_purchases=Count("id", filter=Q(status="completed")),
        total_spent=Sum(
            "listing__price",
            filter=Q(status="completed", completed_at__gte=start_date),
        ),
    )
    purchase_stats = {
        "total_purchases": purchase_agg["total_purchases"] or 0,
        "total_spent": purchase_agg["total_spent"] or Decimal("0.00"),
    }

    # Группировка по дню одним запросом вместо цикла на N count().
    daily_counts = (
        PurchaseRequest.objects.filter(
            seller=user,
            status="completed",
            completed_at__gte=start_date,
        )
        .annotate(day=TruncDate("completed_at"))
        .values("day")
        .annotate(count=Count("id"))
    )
    counts_by_day = {row["day"]: row["count"] for row in daily_counts}
    today = timezone.now().date()
    sales_by_day = [
        {
            "date": (today - timedelta(days=days - i - 1)).strftime("%d.%m"),
            "count": counts_by_day.get(today - timedelta(days=days - i - 1), 0),
        }
        for i in range(days)
    ]

    popular_listings = (
        Listing.objects.filter(seller=user)
        .annotate(views_count=Count("views"))
        .order_by("-views_count")[:5]
    )

    reviews_qs = Review.objects.filter(reviewed_user=user)
    reviews_agg = reviews_qs.aggregate(total=Count("id"), avg=Avg("rating"))
    reviews_stats = {
        "total_reviews": reviews_agg["total"] or 0,
        "avg_rating": reviews_agg["avg"] or 0,
        "recent_reviews": reviews_qs.select_related("reviewer").order_by("-created_at")[:5],
    }

    context = {
        "sales_stats": sales_stats,
        "purchase_stats": purchase_stats,
        "sales_by_day_json": json.dumps(sales_by_day),
        "popular_listings": popular_listings,
        "reviews_stats": reviews_stats,
        "period": period,
    }
    return render(request, "accounts/analytics_dashboard.html", context)


@login_required
def export_data(request):
    """Экспорт данных в CSV."""
    data_type = request.GET.get("type", "sales")

    response = HttpResponse(content_type="text/csv; charset=utf-8-sig")
    response["Content-Disposition"] = f'attachment; filename="lootlink_{data_type}.csv"'
    response.write("\ufeff")  # BOM для корректного открытия в Excel

    writer = csv.writer(response)

    if data_type == "sales":
        writer.writerow(["Дата", "Товар", "Покупатель", "Цена", "Статус"])
        rows = (
            PurchaseRequest.objects.filter(seller=request.user)
            .select_related("listing", "buyer")
            .order_by("-created_at")
            .iterator(chunk_size=500)
        )
        for sale in rows:
            writer.writerow(
                [
                    sale.created_at.strftime("%d.%m.%Y %H:%M"),
                    sale.listing.title,
                    sale.buyer.username,
                    str(sale.listing.price),
                    sale.get_status_display(),
                ]
            )

    elif data_type == "purchases":
        writer.writerow(["Дата", "Товар", "Продавец", "Цена", "Статус"])
        rows = (
            PurchaseRequest.objects.filter(buyer=request.user)
            .select_related("listing", "seller")
            .order_by("-created_at")
            .iterator(chunk_size=500)
        )
        for purchase in rows:
            writer.writerow(
                [
                    purchase.created_at.strftime("%d.%m.%Y %H:%M"),
                    purchase.listing.title,
                    purchase.seller.username,
                    str(purchase.listing.price),
                    purchase.get_status_display(),
                ]
            )

    elif data_type == "listings":
        writer.writerow(["Название", "Игра", "Цена", "Статус", "Дата создания"])
        rows = (
            Listing.objects.filter(seller=request.user)
            .select_related("game")
            .order_by("-created_at")
            .iterator(chunk_size=500)
        )
        for listing in rows:
            writer.writerow(
                [
                    listing.title,
                    listing.game.name,
                    str(listing.price),
                    listing.get_status_display(),
                    listing.created_at.strftime("%d.%m.%Y %H:%M"),
                ]
            )

    return response
