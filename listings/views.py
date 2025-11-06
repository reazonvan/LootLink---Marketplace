from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from django.core.mail import mail_admins
from django.views.decorators.http import require_http_methods, require_POST
from django.views.decorators.csrf import ensure_csrf_cookie
from django.core.exceptions import ObjectDoesNotExist
from .models import Listing, Game, Category, Favorite, Report
from .forms import ListingCreateForm, ListingUpdateForm, ListingFilterForm
from .forms_reports import ReportForm
import logging

logger = logging.getLogger(__name__)
security_logger = logging.getLogger('django.security')


def landing_page(request):
    """
    Главная страница (Landing Page).
    
    ВАЖНО: Эта страница НЕ должна кэшироваться полностью, так как содержит
    персонализированный контент (информацию о пользователе в навигации).
    Кэшируется только статистика.
    """
    from accounts.models import CustomUser
    from transactions.models import PurchaseRequest
    from django.core.cache import cache
    from django.db.models import Count
    
    # Последние объявления для отображения
    latest_listings = Listing.objects.filter(status='active').select_related('game', 'seller')[:8]
    
    # Популярные игры с счетчиком объявлений
    games_with_counts = Game.objects.filter(is_active=True).annotate(
        listings_count=Count('listings', filter=Q(listings__status='active'))
    ).order_by('-listings_count')[:6]
    
    # Кешируем статистику (обновляется каждые 5 минут)
    cache_key = 'homepage_stats'
    stats = cache.get(cache_key)
    
    if stats is None:
        # Реальная статистика из базы данных (с приукрашиванием для презентабельности)
        actual_users = CustomUser.objects.count()
        actual_listings = Listing.objects.filter(status='active').count()
        actual_deals = PurchaseRequest.objects.filter(status='completed').count()
        
        stats = {
            'total_listings': max(actual_listings, 150),  # Минимум показываем 150
            'total_users': max(actual_users, 500),  # Минимум показываем 500
            'total_deals': max(actual_deals, 230),  # Минимум показываем 230
        }
        # Кешируем на 5 минут (300 секунд)
        cache.set(cache_key, stats, 300)
    
    context = {
        'latest_listings': latest_listings,
        'games': games_with_counts,  # Теперь с счетчиками
        'stats': stats,  # Передаем stats напрямую
        'total_listings': stats['total_listings'],  # Для совместимости
        'total_users': stats['total_users'],
        'total_deals': stats['total_deals'],
    }
    
    return render(request, 'listings/landing_page.html', context)


def games_catalog(request):
    """Каталог игр с категориями (как на Funpay)."""
    from django.core.cache import cache
    from django.db.models import Count
    
    # Получаем все активные игры с их категориями и подсчетом объявлений
    games = list(Game.objects.filter(is_active=True).prefetch_related(
        'categories'
    ).annotate(
        listings_count=Count('listings', filter=Q(listings__status='active'))
    ).order_by('name'))
    
    # Собираем алфавит и помечаем первую игру каждой буквы
    alphabet = []
    last_letter = None
    
    for game in games:
        # Определяем первую букву
        first_char = game.name[0].upper()
        
        # Для латиницы и кириллицы
        if first_char.isalpha() or first_char.isdigit():
            game.first_letter = first_char
        else:
            game.first_letter = '#'
        
        # Помечаем если это первая игра с этой буквой
        if game.first_letter != last_letter:
            game.first_in_letter = True
            if game.first_letter not in alphabet:
                alphabet.append(game.first_letter)
            last_letter = game.first_letter
        else:
            game.first_in_letter = False
        
        # Добавляем счетчик объявлений для каждой категории
        for category in game.categories.all():
            category.count = Listing.objects.filter(
                game=game,
                category=category,
                status='active'
            ).count()
    
    context = {
        'games': games,
        'alphabet': alphabet,
    }
    
    return render(request, 'listings/games_catalog.html', context)


# Старая функция catalog() удалена - теперь используем games_catalog()


@ensure_csrf_cookie
def listing_detail(request, pk):
    """Детальная страница объявления с похожими предложениями."""
    listing = get_object_or_404(
        Listing.objects.select_related('game', 'seller__profile'),
        pk=pk
    )
    
    # Проверяем, есть ли активный запрос на покупку от текущего пользователя
    user_has_request = False
    is_favorited = False
    
    if request.user.is_authenticated:
        from transactions.models import PurchaseRequest
        user_has_request = PurchaseRequest.objects.filter(
            listing=listing,
            buyer=request.user,
            status__in=['pending', 'accepted']
        ).exists()
        
        # Проверяем, добавлено ли объявление в избранное
        is_favorited = Favorite.objects.filter(
            user=request.user,
            listing=listing
        ).exists()
    
    # Похожие объявления (та же игра, не текущее, активные)
    similar_listings = Listing.objects.filter(
        game=listing.game,
        status='active'
    ).exclude(pk=listing.pk)\
     .select_related('seller', 'seller__profile')\
     .order_by('?')[:4]  # 4 случайных похожих товара
    
    context = {
        'listing': listing,
        'user_has_request': user_has_request,
        'is_favorited': is_favorited,
        'similar_listings': similar_listings,
    }
    
    return render(request, 'listings/listing_detail.html', context)


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
    if hasattr(profile, 'is_verified') and not profile.is_verified:
        messages.warning(
            request,
            '⚠️ Рекомендуем подтвердить email для повышения доверия к вашим объявлениям. '
            '<a href="/accounts/resend-verification/" class="alert-link">Отправить письмо повторно</a>',
            extra_tags='safe'  # Разрешаем HTML в сообщении
        )
    
    # Проверка лимита активных объявлений
    active_listings_count = request.user.listings.filter(status='active').count()
    MAX_ACTIVE_LISTINGS = 50  # Лимит активных объявлений
    
    if active_listings_count >= MAX_ACTIVE_LISTINGS:
        messages.error(
            request,
            f'Достигнут максимальный лимит активных объявлений ({MAX_ACTIVE_LISTINGS}). '
            f'Удалите или завершите некоторые объявления перед созданием новых.'
        )
        return redirect('accounts:my_listings')
    
    if request.method == 'POST':
        try:
            form = ListingCreateForm(request.POST, request.FILES)
            if form.is_valid():
                listing = form.save(commit=False)
                listing.seller = request.user
                listing.save()
                messages.success(request, 'Объявление успешно создано!')
                return redirect('listings:listing_detail', pk=listing.pk)
            else:
                messages.error(request, 'Пожалуйста, исправьте ошибки в форме.')
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f'Ошибка при создании объявления: {e}')
            messages.error(request, 'Произошла ошибка при создании объявления. Попробуйте еще раз.')
            form = ListingCreateForm()
    else:
        form = ListingCreateForm()
    
    context = {
        'form': form,
        'active_listings_count': active_listings_count,
        'max_listings': MAX_ACTIVE_LISTINGS,
    }
    
    return render(request, 'listings/listing_create.html', context)


@login_required
def listing_edit(request, pk):
    """Редактирование объявления."""
    listing = get_object_or_404(Listing, pk=pk, seller=request.user)
    
    if request.method == 'POST':
        form = ListingUpdateForm(request.POST, request.FILES, instance=listing)
        if form.is_valid():
            form.save()
            messages.success(request, 'Объявление успешно обновлено!')
            return redirect('listings:listing_detail', pk=listing.pk)
    else:
        form = ListingUpdateForm(instance=listing)
    
    context = {
        'form': form,
        'listing': listing,
    }
    
    return render(request, 'listings/listing_edit.html', context)


@login_required
def listing_delete(request, pk):
    """Удаление объявления с защитой транзакцией."""
    from django.db import transaction
    
    listing = get_object_or_404(Listing, pk=pk, seller=request.user)
    
    # Проверка: нельзя удалить объявление с активными запросами на покупку
    from transactions.models import PurchaseRequest
    active_requests = PurchaseRequest.objects.filter(
        listing=listing,
        status__in=['pending', 'accepted']
    )
    
    if active_requests.exists():
        messages.error(
            request, 
            'Нельзя удалить объявление с активными запросами на покупку. '
            'Сначала завершите или отклоните все запросы.'
        )
        return redirect('listings:listing_detail', pk=pk)
    
    if request.method == 'POST':
        # Используем транзакцию для атомарного удаления
        with transaction.atomic():
            listing.delete()
        messages.success(request, 'Объявление удалено.')
        return redirect('accounts:my_listings')
    
    context = {
        'listing': listing,
    }
    
    return render(request, 'listings/listing_delete.html', context)


def category_listings(request, game_slug, category_slug):
    """Объявления конкретной категории игры с динамическими фильтрами."""
    from .models_filters import CategoryFilter, ListingFilterValue
    from django.db.models import Prefetch
    
    game = get_object_or_404(Game, slug=game_slug, is_active=True)
    category = get_object_or_404(Category, slug=category_slug, game=game, is_active=True)
    
    # Получаем активные фильтры для этой категории
    category_filters = CategoryFilter.objects.filter(
        category=category,
        is_active=True
    ).prefetch_related('options').order_by('order')
    
    # Получаем объявления этой категории
    listings = Listing.objects.filter(
        game=game,
        category=category,
        status='active'
    ).select_related('seller', 'seller__profile').prefetch_related(
        Prefetch('filter_values', queryset=ListingFilterValue.objects.select_related('category_filter'))
    )
    
    # Применяем фильтры из GET параметров
    applied_filters = {}
    for category_filter in category_filters:
        filter_value = request.GET.get(category_filter.field_name)
        if filter_value:
            applied_filters[category_filter.field_name] = filter_value
            # Фильтруем объявления
            if category_filter.filter_type in ['select', 'multiselect']:
                listings = listings.filter(
                    filter_values__category_filter=category_filter,
                    filter_values__value_text=filter_value
                )
            elif category_filter.filter_type == 'checkbox':
                listings = listings.filter(
                    filter_values__category_filter=category_filter,
                    filter_values__value_bool=True
                )
    
    # Сортировка
    sort_by = request.GET.get('sort', '-created_at')
    if sort_by in ['-created_at', 'created_at', 'price', '-price']:
        listings = listings.order_by(sort_by)
    else:
        listings = listings.order_by('-created_at')
    
    # Пагинация
    paginator = Paginator(listings, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'game': game,
        'category': category,
        'page_obj': page_obj,
        'category_filters': category_filters,
        'applied_filters': applied_filters,
        'sort_by': sort_by,
    }
    
    return render(request, 'listings/category_listings.html', context)


def game_listings(request, slug):
    """Объявления конкретной игры с оптимизацией запросов."""
    from django.core.cache import cache
    
    game = get_object_or_404(Game, slug=slug, is_active=True)
    
    # Оптимизация: используем only() для выборки только нужных полей
    listings = Listing.objects.filter(
        game=game,
        status='active'
    ).select_related('seller', 'seller__profile', 'category')\
     .only(
        'id', 'title', 'price', 'image', 'created_at', 'status',
        'seller__username', 'seller__profile__rating', 
        'category__name', 'game__name'
    ).order_by('-created_at')
    
    # Кэшируем категории игры (меняются редко)
    cache_key = f'game_categories_{game.id}'
    categories = cache.get(cache_key)
    
    if categories is None:
        categories = list(game.categories.filter(is_active=True).order_by('order', 'name'))
        cache.set(cache_key, categories, 3600)  # 1 час
    
    # Фильтр по категории
    category_slug = request.GET.get('category')
    if category_slug:
        listings = listings.filter(category__slug=category_slug)
    
    # Пагинация
    paginator = Paginator(listings, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'game': game,
        'categories': categories,
        'page_obj': page_obj,
    }
    
    return render(request, 'listings/game_listings.html', context)


@require_http_methods(["GET"])
def get_categories_by_game(request):
    """API endpoint для получения категорий по игре (для AJAX)"""
    game_id = request.GET.get('game')
    
    if not game_id:
        return JsonResponse({'error': 'game_id required'}, status=400)
    
    try:
        categories = Category.objects.filter(
            game_id=game_id,
            is_active=True
        ).order_by('order', 'name').values('id', 'name', 'icon')
        
        return JsonResponse({
            'categories': list(categories)
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_POST
def toggle_favorite(request, pk):
    """Добавить/убрать из избранного (AJAX)."""
    listing = get_object_or_404(Listing, pk=pk)
    
    favorite = Favorite.objects.filter(user=request.user, listing=listing).first()
    
    if favorite:
        favorite.delete()
        is_favorited = False
        message = 'Удалено из избранного'
    else:
        Favorite.objects.create(user=request.user, listing=listing)
        is_favorited = True
        message = 'Добавлено в избранное'
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'is_favorited': is_favorited,
            'message': message
        })
    
    messages.success(request, message)
    return redirect('listings:listing_detail', pk=pk)


@login_required
def favorites_list(request):
    """Список избранных объявлений."""
    # Исправление N+1 Query Problem
    favorites_listings = Listing.objects.filter(
        favorited_by__user=request.user
    ).select_related('game', 'seller__profile')
    
    # Пагинация
    paginator = Paginator(favorites_listings, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
    }
    
    return render(request, 'listings/favorites.html', context)


@login_required
def report_listing(request, pk):
    """Подать жалобу на объявление."""
    listing = get_object_or_404(Listing, pk=pk)
    
    # Нельзя жаловаться на свое объявление
    if listing.seller == request.user:
        messages.error(request, 'Вы не можете пожаловаться на свое объявление.')
        # Логируем подозрительную активность
        security_logger.warning(
            f'User attempted to report own listing: user={request.user.username} | listing_id={pk}'
        )
        return redirect('listings:listing_detail', pk=pk)
    
    # Проверяем, не подавал ли уже жалобу
    existing_report = Report.objects.filter(
        reporter=request.user,
        listing=listing,
        report_type='listing'
    ).first()
    
    if existing_report:
        messages.info(request, f'Вы уже подали жалобу на это объявление. Статус: {existing_report.get_status_display()}')
        return redirect('listings:listing_detail', pk=pk)
    
    if request.method == 'POST':
        form = ReportForm(request.POST)
        if form.is_valid():
            report = form.save(commit=False)
            report.reporter = request.user
            report.listing = listing
            report.report_type = 'listing'
            report.save()
            
            # Отправляем email администраторам
            try:
                # Используем build_absolute_uri вместо hardcoded URL
                from django.urls import reverse
                listing_url = request.build_absolute_uri(
                    reverse('listings:listing_detail', kwargs={'pk': listing.pk})
                )
                report_admin_url = request.build_absolute_uri(
                    reverse('admin:listings_report_change', args=[report.pk])
                )
                
                mail_admins(
                    subject=f'Новая жалоба на объявление: {listing.title}',
                    message=f"""
Пользователь: {request.user.username}
Объявление: {listing.title} (ID: {listing.pk})
Продавец: {listing.seller.username}
Причина: {report.get_reason_display()}

Описание:
{report.description}

Ссылка на объявление: {listing_url}
Ссылка на жалобу (админка): {report_admin_url}
                    """,
                    fail_silently=True
                )
            except Exception as e:
                logger.error(f'Ошибка отправки email админам при жалобе на объявление: {e}')
            
            messages.success(request, 'Жалоба отправлена. Администрация рассмотрит её в ближайшее время.')
            return redirect('listings:listing_detail', pk=pk)
    else:
        form = ReportForm()
    
    context = {
        'form': form,
        'listing': listing,
    }
    
    return render(request, 'listings/report_listing.html', context)


@login_required
def report_user(request, username):
    """Подать жалобу на пользователя."""
    from accounts.models import CustomUser
    reported_user = get_object_or_404(CustomUser, username=username)
    
    # Нельзя жаловаться на себя
    if reported_user == request.user:
        messages.error(request, 'Вы не можете пожаловаться на себя.')
        return redirect('accounts:profile', username=username)
    
    # Проверяем, не подавал ли уже жалобу
    existing_report = Report.objects.filter(
        reporter=request.user,
        reported_user=reported_user,
        report_type='user'
    ).first()
    
    if existing_report:
        messages.info(request, f'Вы уже подали жалобу на этого пользователя. Статус: {existing_report.get_status_display()}')
        return redirect('accounts:profile', username=username)
    
    if request.method == 'POST':
        form = ReportForm(request.POST)
        if form.is_valid():
            report = form.save(commit=False)
            report.reporter = request.user
            report.reported_user = reported_user
            report.report_type = 'user'
            report.save()
            
            # Отправляем email администраторам
            try:
                # Используем build_absolute_uri вместо hardcoded URL
                from django.urls import reverse
                profile_url = request.build_absolute_uri(
                    reverse('accounts:profile', kwargs={'username': reported_user.username})
                )
                report_admin_url = request.build_absolute_uri(
                    reverse('admin:listings_report_change', args=[report.pk])
                )
                
                mail_admins(
                    subject=f'Новая жалоба на пользователя: {reported_user.username}',
                    message=f"""
Жалобщик: {request.user.username}
Пользователь: {reported_user.username}
Причина: {report.get_reason_display()}

Описание:
{report.description}

Ссылка на профиль: {profile_url}
Ссылка на жалобу (админка): {report_admin_url}
                    """,
                    fail_silently=True
                )
            except Exception as e:
                logger.error(f'Ошибка отправки email админам при жалобе на объявление: {e}')
            
            messages.success(request, 'Жалоба отправлена. Администрация рассмотрит её в ближайшее время.')
            return redirect('accounts:profile', username=username)
    else:
        form = ReportForm()
    
    context = {
        'form': form,
        'reported_user': reported_user,
    }
    
    return render(request, 'listings/report_user.html', context)

