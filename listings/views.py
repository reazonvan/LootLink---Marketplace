import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from django.core.exceptions import ObjectDoesNotExist
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods, require_POST

from .forms import ListingCreateForm, ListingFilterForm, ListingUpdateForm
from .forms_reports import ReportForm
from .models import Category, Favorite, Game, Listing, Report

logger = logging.getLogger(__name__)
security_logger = logging.getLogger("django.security")


def landing_page(request):
    """Главная страница (Landing Page).

    P2-8: данные кешируются на 5 минут — публичный контент,
    меняется редко, общий для всех пользователей.
    Q9: защита от cache stampede через short-lived lock — когда TTL истёк,
    только один request пересчитает данные, остальные отдадут предыдущий
    кэш (stale-while-revalidate подход через `_warming` маркер).
    """
    from django.core.cache import cache
    from django.db.models import Count

    from core.utils import get_platform_stats

    CACHE_KEY = "landing_page_data_v1"
    CACHE_TTL = 300
    LOCK_KEY = "landing_page_data_v1__lock"
    LOCK_TTL = 30  # таймаут на пересчёт

    cached = cache.get(CACHE_KEY)
    # Q9: cache.add возвращает True только если ключ свободен — атомарный lock.
    # При промахе кэша лочимся; параллельные запросы пойдут дальше с cached=None
    # и отрендерят страницу без кэша (graceful degradation) либо подождут.
    if cached is None and cache.add(LOCK_KEY, "1", LOCK_TTL):
        from accounts.models import Profile
        from transactions.models import Review

        try:
            latest_listings = list(
                Listing.objects.filter(status="active", seller__is_active=True).select_related(
                    "game", "seller"
                )[:8]
            )
            games_with_counts = list(
                Game.objects.filter(is_active=True)
                .annotate(listings_count=Count("listings", filter=Q(listings__status="active")))
                .order_by("-listings_count")[:6]
            )
            real_reviews = list(
                Review.objects.filter(rating__gte=4, reviewer__is_active=True)
                .select_related("reviewer", "purchase_request__listing")
                .order_by("-created_at")[:3]
            )
            top_sellers = list(
                Profile.objects.filter(
                    user__is_active=True,
                    user__is_deleted=False,
                    rating__gt=0,
                    total_sales__gt=0,
                )
                .select_related("user")
                .order_by("-rating", "-total_sales")[:3]
            )
            cached = {
                "latest_listings": latest_listings,
                "games": games_with_counts,
                "real_reviews": real_reviews,
                "top_sellers": top_sellers,
            }
            cache.set(CACHE_KEY, cached, CACHE_TTL)
        finally:
            cache.delete(LOCK_KEY)
    elif cached is None:
        # Lock уже взят другим worker'ом — отдаём пустые списки,
        # шаблон умеет рендериться с empty state.
        cached = {
            "latest_listings": [],
            "games": [],
            "real_reviews": [],
            "top_sellers": [],
        }

    stats = get_platform_stats()

    context = {
        **cached,
        "stats": stats,
        "total_listings": stats["total_listings"],
        "total_users": stats["active_users"],
        "total_deals": stats["total_deals"],
    }

    return render(request, "listings/landing_page.html", context)


def games_catalog(request):
    """Каталог: алфавитный список игр с категориями-ссылками.

    Контекст кэшируется в Redis на 5 минут — ORM (770 игр + 3765 категорий
    с annotate) стоит ~325 мс, шаблон ~670 мс. Сам каталог редко меняется
    (правится через админку или management command), поэтому stale-окно
    в 5 минут безопасно. Инвалидация — `cache.delete('games_catalog_ctx_v1')`.
    """
    from collections import OrderedDict

    from django.core.cache import cache
    from django.db.models import Count, Min, Prefetch

    CACHE_KEY = "games_catalog_ctx_v1"
    CACHE_TTL = 600  # 10 минут (Celery beat прогревает каждые 4 минуты)

    context = cache.get(CACHE_KEY)
    if context is None:
        categories_qs = (
            Category.objects.filter(is_active=True)
            .annotate(
                listings_count=Count("listings", filter=Q(listings__status="active")),
                min_price=Min("listings__price", filter=Q(listings__status="active")),
            )
            .order_by("order", "name")
        )

        games = list(
            Game.objects.filter(is_active=True)
            .prefetch_related(
                Prefetch("categories", queryset=categories_qs, to_attr="active_categories")
            )
            .annotate(listings_count=Count("listings", filter=Q(listings__status="active")))
            .order_by("name")
        )

        total_listings = sum(g.listings_count or 0 for g in games)
        total_categories = sum(len(g.active_categories) for g in games)

        alphabet_groups = OrderedDict()
        for game in games:
            first_char = game.name[0].upper() if game.name else "#"
            if first_char.isdigit():
                first_char = "0-9"
            alphabet_groups.setdefault(first_char, []).append(game)

        context = {
            "games": games,
            "total_listings": total_listings,
            "total_categories": total_categories,
            "alphabet_groups": alphabet_groups,
            "alphabet_letters": list(alphabet_groups.keys()),
        }
        cache.set(CACHE_KEY, context, CACHE_TTL)

    return render(request, "listings/games_catalog.html", context)


# Старая функция catalog() удалена - теперь используем games_catalog()


@ensure_csrf_cookie
def listing_detail(request, pk):
    """Детальная страница объявления с похожими предложениями."""
    listing = get_object_or_404(Listing.objects.select_related("game", "seller__profile"), pk=pk)

    # Записываем просмотр в историю
    from listings.models_history import ViewHistory

    if request.user.is_authenticated:
        ViewHistory.record_view(request.user, listing)

    # Считаем уникальные просмотры
    views_count = ViewHistory.objects.filter(listing=listing).count()

    # Проверяем, есть ли активный запрос на покупку от текущего пользователя
    user_has_request = False
    is_favorited = False

    if request.user.is_authenticated:
        from transactions.models import PurchaseRequest

        user_has_request = PurchaseRequest.objects.filter(
            listing=listing, buyer=request.user, status__in=["pending", "accepted"]
        ).exists()

        # Проверяем, добавлено ли объявление в избранное
        is_favorited = Favorite.objects.filter(user=request.user, listing=listing).exists()

    # Похожие объявления (та же игра, не текущее, активные)
    # Используем последние по дате вместо ORDER BY RANDOM() (full table scan)
    similar_listings = (
        Listing.objects.filter(game=listing.game, status="active")
        .exclude(pk=listing.pk)
        .select_related("seller", "seller__profile")
        .order_by("-created_at")[:4]
    )

    context = {
        "listing": listing,
        "views_count": views_count,
        "user_has_request": user_has_request,
        "is_favorited": is_favorited,
        "similar_listings": similar_listings,
    }

    return render(request, "listings/listing_detail.html", context)


@login_required
def listing_create(request):
    """Создание нового объявления."""
    # Проверяем наличие профиля и создаем его если нужно
    try:
        profile = request.user.profile
    except (AttributeError, ObjectDoesNotExist):
        from accounts.models import Profile

        profile = Profile.objects.create(user=request.user)

    # Проверка email верификации (SOFT MODE - предупреждение, но не блокировка)
    if hasattr(profile, "is_verified") and not profile.is_verified:
        messages.warning(
            request,
            "Рекомендуем подтвердить email для повышения доверия к вашим объявлениям. "
            "Отправить письмо повторно",
            extra_tags="resend_verification",
        )

    from django.conf import settings as django_settings
    from django.db import transaction as db_transaction

    max_listings = django_settings.MAX_ACTIVE_LISTINGS
    # Считаем для UI, фактическую проверку делаем под select_for_update ниже.
    active_listings_count = request.user.listings.filter(status="active").count()

    if active_listings_count >= max_listings:
        messages.error(
            request,
            f"Достигнут максимальный лимит активных объявлений ({max_listings}). "
            f"Удалите или завершите некоторые объявления перед созданием новых.",
        )
        return redirect("accounts:my_listings")

    if request.method == "POST":
        try:
            form = ListingCreateForm(request.POST, request.FILES)
            if form.is_valid():
                from accounts.models import CustomUser

                with db_transaction.atomic():
                    # Блокируем пользователя — гарантия что лимит не обойти
                    # параллельными запросами (P1-3 race condition).
                    locked_user = CustomUser.objects.select_for_update().get(pk=request.user.pk)
                    current_active = Listing.objects.filter(
                        seller=locked_user, status="active"
                    ).count()
                    if current_active >= max_listings:
                        messages.error(
                            request,
                            f"Достигнут максимальный лимит активных объявлений ({max_listings}).",
                        )
                        return redirect("accounts:my_listings")
                    listing = form.save(commit=False)
                    listing.seller = locked_user
                    listing.save()
                messages.success(request, "Объявление успешно создано!")
                return redirect("listings:listing_detail", pk=listing.pk)
            else:
                messages.error(request, "Пожалуйста, исправьте ошибки в форме.")
        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.exception(f"Ошибка при создании объявления: {e}")
            messages.error(request, "Произошла ошибка при создании объявления. Попробуйте еще раз.")
            form = ListingCreateForm()
    else:
        form = ListingCreateForm()

    context = {
        "form": form,
        "active_listings_count": active_listings_count,
        "max_listings": max_listings,
    }

    return render(request, "listings/listing_create.html", context)


@login_required
def listing_edit(request, pk):
    """Редактирование объявления."""
    listing = get_object_or_404(Listing, pk=pk, seller=request.user)

    if request.method == "POST":
        form = ListingUpdateForm(request.POST, request.FILES, instance=listing)
        if form.is_valid():
            form.save()
            messages.success(request, "Объявление успешно обновлено!")
            return redirect("listings:listing_detail", pk=listing.pk)
    else:
        form = ListingUpdateForm(instance=listing)

    context = {
        "form": form,
        "listing": listing,
    }

    return render(request, "listings/listing_edit.html", context)


@login_required
def listing_delete(request, pk):
    """Удаление объявления с защитой транзакцией."""
    from django.db import transaction

    listing = get_object_or_404(Listing, pk=pk, seller=request.user)

    # Проверка: нельзя удалить объявление с активными запросами на покупку
    from transactions.models import PurchaseRequest

    active_requests = PurchaseRequest.objects.filter(
        listing=listing, status__in=["pending", "accepted"]
    )

    if active_requests.exists():
        messages.error(
            request,
            "Нельзя удалить объявление с активными запросами на покупку. "
            "Сначала завершите или отклоните все запросы.",
        )
        return redirect("listings:listing_detail", pk=pk)

    if request.method == "POST":
        # Используем транзакцию для атомарного удаления
        with transaction.atomic():
            listing.delete()
        messages.success(request, "Объявление удалено.")
        return redirect("accounts:my_listings")

    context = {
        "listing": listing,
    }

    return render(request, "listings/listing_delete.html", context)


def category_listings(request, game_slug, category_slug):
    """Объявления конкретной категории игры с динамическими фильтрами."""
    from django.db.models import Prefetch

    from .models_filters import CategoryFilter, ListingFilterValue

    game = get_object_or_404(Game, slug=game_slug, is_active=True)
    category = get_object_or_404(Category, slug=category_slug, game=game, is_active=True)

    # Получаем активные фильтры для этой категории
    category_filters = (
        CategoryFilter.objects.filter(category=category, is_active=True)
        .prefetch_related("options")
        .order_by("order")
    )

    # Получаем объявления этой категории
    listings = (
        Listing.objects.filter(game=game, category=category, status="active")
        .select_related("seller", "seller__profile")
        .prefetch_related(
            Prefetch(
                "filter_values",
                queryset=ListingFilterValue.objects.select_related("category_filter"),
            )
        )
    )

    # Применяем фильтры из GET параметров
    applied_filters = {}
    for category_filter in category_filters:
        filter_value = request.GET.get(category_filter.field_name)
        if filter_value:
            applied_filters[category_filter.field_name] = filter_value
            # Фильтруем объявления
            if category_filter.filter_type in ["select", "multiselect"]:
                listings = listings.filter(
                    filter_values__category_filter=category_filter,
                    filter_values__value_text=filter_value,
                )
            elif category_filter.filter_type == "checkbox":
                listings = listings.filter(
                    filter_values__category_filter=category_filter, filter_values__value_bool=True
                )

    # Сортировка
    sort_by = request.GET.get("sort", "-created_at")
    if sort_by in ["-created_at", "created_at", "price", "-price"]:
        listings = listings.order_by(sort_by)
    else:
        listings = listings.order_by("-created_at")

    # Пагинация
    paginator = Paginator(listings, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "game": game,
        "category": category,
        "page_obj": page_obj,
        "category_filters": category_filters,
        "applied_filters": applied_filters,
        "sort_by": sort_by,
    }

    return render(request, "listings/category_listings.html", context)


def game_listings(request, game_slug):
    """Страница игры: категории с подсчётом лотов + последние объявления."""
    from django.db.models import Count

    game = get_object_or_404(Game, slug=game_slug, is_active=True)

    # Категории с подсчётом активных лотов
    categories = list(
        game.categories.filter(is_active=True)
        .annotate(listings_count=Count("listings", filter=Q(listings__status="active")))
        .order_by("order", "name")
    )

    # Общее число лотов игры
    total_listings = sum(c.listings_count for c in categories)

    context = {
        "game": game,
        "categories": categories,
        "total_listings": total_listings,
    }

    return render(request, "listings/game_listings.html", context)


@require_http_methods(["GET"])
def get_categories_by_game(request):
    """API endpoint для получения категорий по игре (для AJAX, legacy by id)."""
    game_id = request.GET.get("game")

    if not game_id:
        return JsonResponse({"error": "game_id required"}, status=400)

    try:
        categories = (
            Category.objects.filter(game_id=game_id, is_active=True)
            .order_by("order", "name")
            .values("id", "name", "icon")
        )

        return JsonResponse({"categories": list(categories)})
    except Exception:
        logger.exception("Error fetching categories for game %s", game_id)
        return JsonResponse({"error": "Ошибка загрузки категорий"}, status=500)


@require_http_methods(["GET"])
def game_categories_api(request, game_slug):
    """Возвращает категории игры (slug + listings_count) для аккордеона каталога.

    Используется на странице `/catalog/` для lazy-load категорий по клику —
    позволяет НЕ рендерить ~3.7к ссылок в HTML и срезать DOM с 14k до ~2k узлов.

    Кэшируется в Redis на 5 минут (`game_cats:<slug>`). Инвалидация — через
    timeout или ручной `cache.delete('game_cats:<slug>')` при изменении
    категорий/листингов.
    """
    from django.core.cache import cache
    from django.db.models import Count

    cache_key = f"game_cats:{game_slug}"
    data = cache.get(cache_key)
    if data is None:
        game = get_object_or_404(Game, slug=game_slug, is_active=True)
        cats = list(
            game.categories.filter(is_active=True)
            .annotate(listings_count=Count("listings", filter=Q(listings__status="active")))
            .order_by("order", "name")
            .values("slug", "name", "listings_count")
        )
        data = {"categories": cats}
        cache.set(cache_key, data, 300)  # 5 минут
    return JsonResponse(data)


@login_required
@require_POST
def toggle_favorite(request, pk):
    """Добавить/убрать из избранного (AJAX).

    Защита от race-condition: unique_together(user, listing) + try/except.
    Параллельные клики не создадут дубликат.
    """
    from django.db import IntegrityError

    listing = get_object_or_404(Listing, pk=pk)

    # Нельзя добавить в избранное собственное объявление
    if listing.seller_id == request.user.id:
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse(
                {"success": False, "message": "Нельзя добавить собственное объявление"},
                status=400,
            )
        messages.error(request, "Нельзя добавить собственное объявление в избранное.")
        return redirect("listings:listing_detail", pk=pk)

    deleted, _ = Favorite.objects.filter(user=request.user, listing=listing).delete()
    if deleted:
        is_favorited = False
        message = "Удалено из избранного"
    else:
        try:
            Favorite.objects.create(user=request.user, listing=listing)
            is_favorited = True
            message = "Добавлено в избранное"
        except IntegrityError:
            # Гонка: добавили параллельно — считаем что уже в избранном
            is_favorited = True
            message = "Уже в избранном"

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse({"success": True, "is_favorited": is_favorited, "message": message})

    messages.success(request, message)
    return redirect("listings:listing_detail", pk=pk)


@login_required
def favorites_list(request):
    """Список избранных объявлений."""
    # Исправление N+1 Query Problem
    favorites_listings = Listing.objects.filter(favorited_by__user=request.user).select_related(
        "game", "seller__profile"
    )

    # Пагинация
    paginator = Paginator(favorites_listings, 12)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
    }

    return render(request, "listings/favorites.html", context)


@login_required
def report_listing(request, pk):  # noqa: C901
    """Подать жалобу на объявление с защитой от race-condition дублей."""
    from django.db import IntegrityError
    from django.db import transaction as db_transaction

    listing = get_object_or_404(Listing, pk=pk)

    if listing.seller == request.user:
        messages.error(request, "Вы не можете пожаловаться на свое объявление.")
        security_logger.warning(
            f"User attempted to report own listing: user={request.user.username} | listing_id={pk}"
        )
        return redirect("listings:listing_detail", pk=pk)

    existing_report = Report.objects.filter(
        reporter=request.user, listing=listing, report_type="listing"
    ).first()
    if existing_report:
        messages.info(
            request,
            f"Вы уже подали жалобу на это объявление. Статус: {existing_report.get_status_display()}",
        )
        return redirect("listings:listing_detail", pk=pk)

    if request.method == "POST":
        form = ReportForm(request.POST)
        if form.is_valid():
            try:
                with db_transaction.atomic():
                    # Повторная проверка под блокировкой — закрывает race condition
                    if Report.objects.filter(
                        reporter=request.user,
                        listing=listing,
                        report_type="listing",
                    ).exists():
                        messages.info(request, "Жалоба уже подана.")
                        return redirect("listings:listing_detail", pk=pk)
                    report = form.save(commit=False)
                    report.reporter = request.user
                    report.listing = listing
                    report.report_type = "listing"
                    report.save()
            except IntegrityError:
                messages.info(request, "Жалоба уже подана.")
                return redirect("listings:listing_detail", pk=pk)

            # Email админам — асинхронно через Celery (P2-16): mail_admins был
            # синхронным и подвешивал view при тормозном SMTP.
            try:
                from django.conf import settings as dj_settings
                from django.db import transaction as db_transaction
                from django.urls import reverse

                from core.tasks import send_email_async

                listing_url = request.build_absolute_uri(
                    reverse("listings:listing_detail", kwargs={"pk": listing.pk})
                )
                report_admin_url = request.build_absolute_uri(
                    reverse("admin:listings_report_change", args=[report.pk])
                )
                subject = f"Новая жалоба на объявление: {listing.title}"
                body = (
                    f"Пользователь: {request.user.username}\n"
                    f"Объявление: {listing.title} (ID: {listing.pk})\n"
                    f"Продавец: {listing.seller.username}\n"
                    f"Причина: {report.get_reason_display()}\n\n"
                    f"Описание:\n{report.description}\n\n"
                    f"Ссылка: {listing_url}\n"
                    f"Админка: {report_admin_url}\n"
                )
                admin_emails = [addr for _, addr in getattr(dj_settings, "ADMINS", [])] or [
                    getattr(dj_settings, "SUPPORT_EMAIL", "")
                ]
                for admin_email in admin_emails:
                    if admin_email:
                        db_transaction.on_commit(
                            lambda s=subject, b=body, e=admin_email: send_email_async.delay(s, b, e)
                        )
            except Exception as e:
                logger.error(f"Ошибка постановки email админам в очередь: {e}")

            messages.success(
                request, "Жалоба отправлена. Администрация рассмотрит её в ближайшее время."
            )
            return redirect("listings:listing_detail", pk=pk)
    else:
        form = ReportForm()

    context = {
        "form": form,
        "listing": listing,
    }

    return render(request, "listings/report_listing.html", context)


@login_required
def report_user(request, username):
    """Подать жалобу на пользователя."""
    from accounts.models import CustomUser

    reported_user = get_object_or_404(CustomUser, username=username)

    # Нельзя жаловаться на себя
    if reported_user == request.user:
        messages.error(request, "Вы не можете пожаловаться на себя.")
        return redirect("accounts:profile", username=username)

    # Проверяем, не подавал ли уже жалобу
    existing_report = Report.objects.filter(
        reporter=request.user, reported_user=reported_user, report_type="user"
    ).first()

    if existing_report:
        messages.info(
            request,
            f"Вы уже подали жалобу на этого пользователя. Статус: {existing_report.get_status_display()}",
        )
        return redirect("accounts:profile", username=username)

    if request.method == "POST":
        form = ReportForm(request.POST)
        if form.is_valid():
            report = form.save(commit=False)
            report.reporter = request.user
            report.reported_user = reported_user
            report.report_type = "user"
            report.save()

            # A6: email админам асинхронно через Celery
            # (раньше mail_admins был синхронным — зависал на SMTP-таймауте).
            try:
                from django.conf import settings as dj_settings
                from django.db import transaction as db_transaction
                from django.urls import reverse

                from core.tasks import send_email_async

                profile_url = request.build_absolute_uri(
                    reverse("accounts:profile", kwargs={"username": reported_user.username})
                )
                report_admin_url = request.build_absolute_uri(
                    reverse("admin:listings_report_change", args=[report.pk])
                )
                subject = f"Новая жалоба на пользователя: {reported_user.username}"
                body = (
                    f"Жалобщик: {request.user.username}\n"
                    f"Пользователь: {reported_user.username}\n"
                    f"Причина: {report.get_reason_display()}\n\n"
                    f"Описание:\n{report.description}\n\n"
                    f"Ссылка на профиль: {profile_url}\n"
                    f"Ссылка на жалобу (админка): {report_admin_url}\n"
                )
                admin_emails = [addr for _, addr in getattr(dj_settings, "ADMINS", [])] or [
                    getattr(dj_settings, "SUPPORT_EMAIL", "")
                ]
                for admin_email in admin_emails:
                    if admin_email:
                        db_transaction.on_commit(
                            lambda s=subject, b=body, e=admin_email: send_email_async.delay(s, b, e)
                        )
            except Exception as e:
                logger.error(f"Ошибка постановки email админам в очередь: {e}")

            messages.success(
                request, "Жалоба отправлена. Администрация рассмотрит её в ближайшее время."
            )
            return redirect("accounts:profile", username=username)
    else:
        form = ReportForm()

    context = {
        "form": form,
        "reported_user": reported_user,
    }

    return render(request, "listings/report_user.html", context)
