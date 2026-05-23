from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import connection
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from .models import Notification


def custom_404(request, exception):
    """Кастомная страница 404."""
    return render(request, "404.html", status=404)


def custom_500(request):
    """Кастомная страница 500."""
    return render(request, "500.html", status=500)


def health_check(request):
    """
    Liveness/readiness endpoint для reverse proxy и Docker healthcheck.
    Проверяет доступность БД.
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:
        # Любой сбой БД (OperationalError, InterfaceError, ConnectionError) —
        # endpoint должен ответить 503 чтобы балансер вывел инстанс из ротации.
        import logging

        logging.getLogger(__name__).exception("Health check DB probe failed")
        return JsonResponse({"status": "error"}, status=503)

    return JsonResponse({"status": "ok"})


def about(request):
    """Страница 'О нас' с реальной статистикой из PostgreSQL."""
    from accounts.models import CustomUser
    from listings.models import Game, Listing
    from transactions.models import PurchaseRequest

    # Реальная статистика
    total_users = CustomUser.objects.count()
    total_listings = Listing.objects.filter(status="active").count()
    total_deals = PurchaseRequest.objects.filter(status="completed").count()
    total_games = Game.objects.filter(is_active=True).count()

    context = {
        "total_users": total_users,
        "total_listings": total_listings,
        "total_deals": total_deals,
        "total_games": total_games,
    }

    return render(request, "pages/about.html", context)


def rules(request):
    """Страница 'Правила'."""
    return render(request, "pages/rules.html")


def privacy_policy(request):
    """Политика конфиденциальности (152-ФЗ)."""
    return render(request, "pages/privacy_policy.html")


# ========== СИСТЕМА УВЕДОМЛЕНИЙ ==========


@login_required
def notifications_list(request):
    """Список уведомлений пользователя с пагинацией."""
    notifications = Notification.objects.filter(user=request.user).order_by("-created_at")

    # Пагинация - 20 уведомлений на страницу
    paginator = Paginator(notifications, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
        "notifications": page_obj.object_list,
    }

    return render(request, "core/notifications_list.html", context)


@login_required
@require_http_methods(["POST"])
def mark_notification_read(request, pk):
    """Отметить уведомление как прочитанное."""
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    notification.mark_as_read()

    # Если AJAX запрос
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse({"success": True, "message": "Уведомление отмечено как прочитанное"})

    # Иначе редирект
    return redirect("core:notifications_list")


@login_required
@require_http_methods(["POST"])
def mark_all_notifications_read(request):
    """Отметить все уведомления пользователя как прочитанные."""
    Notification.mark_all_as_read(request.user)

    # Если AJAX запрос
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse(
            {"success": True, "message": "Все уведомления отмечены как прочитанные"}
        )

    # Иначе редирект
    return redirect("core:notifications_list")


@login_required
@require_http_methods(["GET"])
def unread_notifications_count(request):
    """API endpoint для получения количества непрочитанных уведомлений (AJAX)."""
    count = Notification.objects.filter(user=request.user, is_read=False).count()

    return JsonResponse({"count": count})


def yandex_verification(request):
    """Yandex Webmaster verification file."""
    from django.http import HttpResponse

    html_content = """<html>
    <head>
        <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
    </head>
    <body>Verification: a6899228ac192041</body>
</html>"""
    return HttpResponse(html_content, content_type="text/html")


def requisites(request):
    """Страница с реквизитами для платежных систем.

    Все юр-поля приходят из settings и могут быть пустыми — шаблон
    скрывает соответствующие блоки и показывает плашку «оформляются».
    """
    from django.conf import settings as dj_settings

    context = {
        "legal_name": dj_settings.LEGAL_NAME,
        "legal_inn": dj_settings.LEGAL_INN,
        "legal_ogrn": dj_settings.LEGAL_OGRN,
        "legal_ogrn_label": dj_settings.LEGAL_OGRN_LABEL,
        "legal_address": dj_settings.LEGAL_ADDRESS,
        "legal_bank_name": dj_settings.LEGAL_BANK_NAME,
        "legal_bank_bic": dj_settings.LEGAL_BANK_BIC,
        "legal_bank_account": dj_settings.LEGAL_BANK_ACCOUNT,
        "legal_bank_corr": dj_settings.LEGAL_BANK_CORR,
    }
    return render(request, "core/requisites.html", context)
