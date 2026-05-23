"""
Views для кастомной админ-панели
"""

from datetime import timedelta

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import user_passes_test
from django.db.models import Avg, Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.models import CustomUser, Profile
from core.models_audit import DataChangeLog, SecurityAuditLog
from core.utils import paginate_queryset
from listings.models import Category, Game, Listing, Report
from payments.models import Wallet
from payments.models_disputes import Dispute
from transactions.models import PurchaseRequest, Review


def is_staff_or_moderator(user):
    """Проверка: админ или модератор"""
    return user.is_staff or (hasattr(user, "profile") and user.profile.is_moderator)


@user_passes_test(is_staff_or_moderator)
def dashboard(request):
    """
    Главная страница админ-панели с аналитикой.

    P2-1: тяжёлые агрегаты (~30 COUNT/SUM/AVG) закешированы на 60 секунд.
    P2-2: чарты — один TruncDate-запрос вместо N count'ов.
    """
    from django.core.cache import cache
    from django.db.models.functions import TruncDate

    CACHE_KEY = "admin_dashboard_stats_v2"
    CACHE_TTL = 60

    cached = cache.get(CACHE_KEY)
    if cached is None:
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)

        # Графики: один запрос вместо N count'ов
        reg_by_day = {
            r["d"]: r["c"]
            for r in CustomUser.objects.filter(date_joined__date__gte=today - timedelta(days=6))
            .annotate(d=TruncDate("date_joined"))
            .values("d")
            .annotate(c=Count("id"))
        }
        list_by_day = {
            r["d"]: r["c"]
            for r in Listing.objects.filter(created_at__date__gte=today - timedelta(days=6))
            .annotate(d=TruncDate("created_at"))
            .values("d")
            .annotate(c=Count("id"))
        }
        registrations_chart = []
        listings_chart = []
        for i in range(6, -1, -1):
            d = today - timedelta(days=i)
            registrations_chart.append({"date": d.strftime("%d.%m"), "count": reg_by_day.get(d, 0)})
            listings_chart.append({"date": d.strftime("%d.%m"), "count": list_by_day.get(d, 0)})

        cached = {
            "total_users": CustomUser.objects.count(),
            "total_listings": Listing.objects.count(),
            "active_listings": Listing.objects.filter(status="active").count(),
            "total_transactions": PurchaseRequest.objects.filter(status="completed").count(),
            "new_users_today": CustomUser.objects.filter(date_joined__date=today).count(),
            "new_users_week": CustomUser.objects.filter(date_joined__date__gte=week_ago).count(),
            "new_users_month": CustomUser.objects.filter(date_joined__date__gte=month_ago).count(),
            "new_listings_today": Listing.objects.filter(created_at__date=today).count(),
            "new_listings_week": Listing.objects.filter(created_at__date__gte=week_ago).count(),
            "completed_today": PurchaseRequest.objects.filter(
                status="completed", updated_at__date=today
            ).count(),
            "completed_week": PurchaseRequest.objects.filter(
                status="completed", updated_at__date__gte=week_ago
            ).count(),
            "pending_reports": Report.objects.filter(status="pending").count(),
            "active_disputes": Dispute.objects.filter(status__in=["open", "under_review"]).count(),
            "total_balance": float(Wallet.objects.aggregate(total=Sum("balance"))["total"] or 0),
            "avg_transaction": float(
                PurchaseRequest.objects.filter(status="completed").aggregate(avg=Avg("amount"))[
                    "avg"
                ]
                or 0
            ),
            "security_alerts_today": SecurityAuditLog.objects.filter(
                created_at__date=today, risk_level__in=["high", "critical"]
            ).count(),
            "failed_logins_today": SecurityAuditLog.objects.filter(
                created_at__date=today, action_type="login_failed"
            ).count(),
            "registrations_chart": registrations_chart,
            "listings_chart": listings_chart,
        }
        cache.set(CACHE_KEY, cached, CACHE_TTL)

    # Топы и последние активности — не кешируем, чтобы быстро видеть свежее
    top_games = Game.objects.annotate(listings_count=Count("listings")).order_by("-listings_count")[
        :5
    ]
    recent_users = CustomUser.objects.select_related("profile").order_by("-date_joined")[:5]
    recent_listings = Listing.objects.select_related("game", "seller").order_by("-created_at")[:5]
    recent_transactions = PurchaseRequest.objects.select_related("buyer", "listing").order_by(
        "-created_at"
    )[:5]

    context = {
        **cached,
        "top_games": top_games,
        "recent_users": recent_users,
        "recent_listings": recent_listings,
        "recent_transactions": recent_transactions,
    }

    return render(request, "admin_panel/dashboard.html", context)


@user_passes_test(is_staff_or_moderator)
def users_list(request):
    """Список пользователей с фильтрами"""
    users = CustomUser.objects.select_related("profile").all()

    # Фильтры
    role = request.GET.get("role")
    verified = request.GET.get("verified")
    search = request.GET.get("search")

    if role == "admin":
        users = users.filter(is_staff=True)
    elif role == "moderator":
        users = users.filter(profile__is_moderator=True)
    elif role == "verified":
        users = users.filter(profile__is_verified=True)

    if verified == "yes":
        users = users.filter(profile__is_verified=True)
    elif verified == "no":
        users = users.filter(profile__is_verified=False)

    if search:
        users = users.filter(
            Q(username__icontains=search)
            | Q(email__icontains=search)
            | Q(first_name__icontains=search)
            | Q(last_name__icontains=search)
        )

    users = users.order_by("-date_joined")
    page_obj = paginate_queryset(users, request, per_page=50)
    total_count = page_obj.paginator.count

    context = {
        "users": page_obj,
        "page_obj": page_obj,
        "total_count": total_count,
        "filters": {
            "role": role,
            "verified": verified,
            "search": search,
        },
    }

    return render(request, "admin_panel/users_list.html", context)


@user_passes_test(is_staff_or_moderator)
def user_detail(request, user_id):
    """Детальная информация о пользователе"""
    user = get_object_or_404(CustomUser.objects.select_related("profile"), id=user_id)

    # Статистика пользователя
    user_listings = Listing.objects.filter(seller=user).count()
    user_purchases = PurchaseRequest.objects.filter(buyer=user, status="completed").count()
    user_sales = PurchaseRequest.objects.filter(listing__seller=user, status="completed").count()

    # Последняя активность
    recent_listings = Listing.objects.filter(seller=user).order_by("-created_at")[:5]
    recent_purchases = PurchaseRequest.objects.filter(buyer=user).order_by("-created_at")[:5]

    # Логи безопасности
    security_logs = SecurityAuditLog.objects.filter(user=user).order_by("-created_at")[:10]

    context = {
        "user": user,
        "user_listings": user_listings,
        "user_purchases": user_purchases,
        "user_sales": user_sales,
        "recent_listings": recent_listings,
        "recent_purchases": recent_purchases,
        "security_logs": security_logs,
    }

    return render(request, "admin_panel/user_detail.html", context)


@user_passes_test(is_staff_or_moderator)
def listings_moderation(request):
    """Модерация объявлений"""
    listings = (
        Listing.objects.select_related("game", "category", "seller__profile")
        .annotate(views_count=Count("views"))
        .all()
    )

    # Фильтры
    status = request.GET.get("status")
    game = request.GET.get("game")
    search = request.GET.get("search")

    if status:
        listings = listings.filter(status=status)
    else:
        # По умолчанию показываем все объявления
        pass

    if game:
        listings = listings.filter(game_id=game)

    if search:
        listings = listings.filter(
            Q(title__icontains=search)
            | Q(description__icontains=search)
            | Q(seller__username__icontains=search)
        )

    listings = listings.order_by("-created_at")
    page_obj = paginate_queryset(listings, request, per_page=50)
    total_count = page_obj.paginator.count

    # Для фильтра игр
    games = Game.objects.all().order_by("name")

    context = {
        "listings": page_obj,
        "page_obj": page_obj,
        "total_count": total_count,
        "games": games,
        "filters": {
            "status": status,
            "game": game,
            "search": search,
        },
    }

    return render(request, "admin_panel/listings_moderation.html", context)


@user_passes_test(is_staff_or_moderator)
def listing_detail(request, listing_id):
    """Детальный просмотр объявления для модерации"""
    listing = get_object_or_404(
        Listing.objects.select_related("game", "category", "seller__profile"), id=listing_id
    )

    # Репорты на это объявление
    reports = Report.objects.filter(listing=listing).select_related("reporter")

    context = {
        "listing": listing,
        "reports": reports,
    }

    return render(request, "admin_panel/listing_detail.html", context)


@user_passes_test(is_staff_or_moderator)
def transactions_list(request):
    """Список транзакций"""
    transactions = PurchaseRequest.objects.select_related(
        "buyer__profile", "listing__seller__profile", "listing__game"
    ).all()

    # Фильтры
    status = request.GET.get("status")
    search = request.GET.get("search")

    if status:
        transactions = transactions.filter(status=status)

    if search:
        transactions = transactions.filter(
            Q(buyer__username__icontains=search)
            | Q(listing__seller__username__icontains=search)
            | Q(listing__title__icontains=search)
        )

    transactions = transactions.order_by("-created_at")
    page_obj = paginate_queryset(transactions, request, per_page=50)
    total_count = page_obj.paginator.count

    context = {
        "transactions": page_obj,
        "page_obj": page_obj,
        "total_count": total_count,
        "filters": {
            "status": status,
            "search": search,
        },
    }

    return render(request, "admin_panel/transactions_list.html", context)


@user_passes_test(is_staff_or_moderator)
def transaction_detail(request, transaction_id):
    """Детальная информация о транзакции"""
    transaction = get_object_or_404(
        PurchaseRequest.objects.select_related(
            "buyer__profile", "listing__seller__profile", "listing__game"
        ),
        id=transaction_id,
    )

    context = {
        "transaction": transaction,
    }

    return render(request, "admin_panel/transaction_detail.html", context)


@user_passes_test(is_staff_or_moderator)
def disputes_list(request):
    """Список споров"""
    disputes = Dispute.objects.select_related(
        "purchase_request__buyer", "purchase_request__listing__seller", "purchase_request__listing"
    ).all()

    # Фильтры
    status = request.GET.get("status", "open")

    if status:
        if status == "active":
            disputes = disputes.filter(status__in=["open", "under_review"])
        else:
            disputes = disputes.filter(status=status)

    disputes = disputes.order_by("-created_at")
    page_obj = paginate_queryset(disputes, request, per_page=50)
    total_count = page_obj.paginator.count

    context = {
        "disputes": page_obj,
        "page_obj": page_obj,
        "total_count": total_count,
        "filters": {
            "status": status,
        },
    }

    return render(request, "admin_panel/disputes_list.html", context)


@user_passes_test(is_staff_or_moderator)
def dispute_detail(request, dispute_id):
    """Детальная информация о споре"""
    dispute = get_object_or_404(
        Dispute.objects.select_related(
            "purchase_request__buyer__profile",
            "purchase_request__listing__seller__profile",
            "purchase_request__listing__game",
            "moderator",
        ).prefetch_related("evidence"),
        id=dispute_id,
    )

    context = {
        "dispute": dispute,
    }

    return render(request, "admin_panel/dispute_detail.html", context)


@user_passes_test(is_staff_or_moderator)
def reports_list(request):
    """Список жалоб"""
    reports = Report.objects.select_related("listing__seller", "listing__game", "reporter").all()

    # Фильтры
    status = request.GET.get("status", "pending")

    if status:
        reports = reports.filter(status=status)

    reports = reports.order_by("-created_at")
    page_obj = paginate_queryset(reports, request, per_page=50)
    total_count = page_obj.paginator.count

    context = {
        "reports": page_obj,
        "page_obj": page_obj,
        "total_count": total_count,
        "filters": {
            "status": status,
        },
    }

    return render(request, "admin_panel/reports_list.html", context)


@user_passes_test(is_staff_or_moderator)
def security_logs(request):
    """Логи безопасности"""
    logs = SecurityAuditLog.objects.select_related("user").all()

    # Фильтры
    risk_level = request.GET.get("risk_level")
    action_type = request.GET.get("action_type")
    date_from = request.GET.get("date_from")
    date_to = request.GET.get("date_to")

    if risk_level:
        logs = logs.filter(risk_level=risk_level)

    if action_type:
        logs = logs.filter(action_type=action_type)

    if date_from:
        logs = logs.filter(created_at__date__gte=date_from)

    if date_to:
        logs = logs.filter(created_at__date__lte=date_to)

    logs = logs.order_by("-created_at")
    page_obj = paginate_queryset(logs, request, per_page=100)
    total_count = page_obj.paginator.count

    context = {
        "logs": page_obj,
        "page_obj": page_obj,
        "total_count": total_count,
        "filters": {
            "risk_level": risk_level,
            "action_type": action_type,
            "date_from": date_from,
            "date_to": date_to,
        },
    }

    return render(request, "admin_panel/security_logs.html", context)


@staff_member_required
def settings(request):
    """Настройки админ-панели"""
    from django.conf import settings as django_settings

    context = {
        "debug": django_settings.DEBUG,
        "allowed_hosts": django_settings.ALLOWED_HOSTS,
        "database": django_settings.DATABASES["default"]["ENGINE"],
        "redis_enabled": django_settings.USE_REDIS,
    }

    return render(request, "admin_panel/settings.html", context)
