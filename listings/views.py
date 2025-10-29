from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from django.core.mail import mail_admins
from django.views.decorators.http import require_http_methods, require_POST
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_exempt
from django.core.exceptions import ObjectDoesNotExist
from .models import Listing, Game, Category, Favorite, Report
from .forms import ListingCreateForm, ListingUpdateForm, ListingFilterForm
from .forms_reports import ReportForm
import logging

logger = logging.getLogger(__name__)


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
    
    # Последние объявления для отображения
    latest_listings = Listing.objects.filter(status='active').select_related('game', 'seller')[:8]
    
    # Популярные игры
    games = Game.objects.filter(is_active=True)[:6]
    
    # Кешируем статистику (обновляется каждые 5 минут)
    cache_key = 'homepage_stats'
    stats = cache.get(cache_key)
    
    if stats is None:
        # Реальная статистика из базы данных
        stats = {
            'total_listings': Listing.objects.filter(status='active').count(),
            'total_users': CustomUser.objects.count(),
            'total_deals': PurchaseRequest.objects.filter(status='completed').count(),
        }
        # Кешируем на 5 минут (300 секунд)
        cache.set(cache_key, stats, 300)
    
    context = {
        'latest_listings': latest_listings,
        'games': games,
        'stats': stats,  # Передаем stats напрямую
        'total_listings': stats['total_listings'],  # Для совместимости
        'total_users': stats['total_users'],
        'total_deals': stats['total_deals'],
    }
    
    return render(request, 'listings/landing_page.html', context)


def catalog(request):
    """Главная страница с каталогом объявлений."""
    listings = Listing.objects.filter(status='active').select_related('game', 'seller')
    
    # Фильтрация
    filter_form = ListingFilterForm(request.GET)
    
    if filter_form.is_valid():
        # Фильтр по игре
        game = filter_form.cleaned_data.get('game')
        if game:
            listings = listings.filter(game=game)
        
        # Фильтр по цене
        min_price = filter_form.cleaned_data.get('min_price')
        if min_price:
            listings = listings.filter(price__gte=min_price)
        
        max_price = filter_form.cleaned_data.get('max_price')
        if max_price:
            listings = listings.filter(price__lte=max_price)
        
        # Поиск по названию (используем PostgreSQL Full-Text Search)
        search = filter_form.cleaned_data.get('search')
        if search:
            # Создаем поисковый запрос с русской морфологией
            search_query = SearchQuery(search, config='russian')
            
            # Используем search_vector для Full-Text Search
            listings = listings.annotate(
                rank=SearchRank('search_vector', search_query)
            ).filter(search_vector=search_query).order_by('-rank', '-created_at')
        
        # Сортировка
        sort = filter_form.cleaned_data.get('sort')
        if sort:
            listings = listings.order_by(sort)
    
    # Пагинация
    paginator = Paginator(listings, 12)  # 12 объявлений на страницу
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Список игр для быстрого доступа
    games = Game.objects.filter(is_active=True)
    
    context = {
        'page_obj': page_obj,
        'filter_form': filter_form,
        'games': games,
    }
    
    return render(request, 'listings/catalog.html', context)


@ensure_csrf_cookie
def listing_detail(request, pk):
    """Детальная страница объявления."""
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
    
    context = {
        'listing': listing,
        'user_has_request': user_has_request,
        'is_favorited': is_favorited,
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
    
    # Проверка email верификации (только если is_verified установлен в False)
    # Временно отключаем эту проверку для решения проблемы с доступом
    # TODO: Включить после того как все пользователи верифицируют email
    # if hasattr(profile, 'is_verified') and not profile.is_verified:
    #     messages.warning(
    #         request,
    #         'Для создания объявлений необходимо подтвердить email. '
    #         'Проверьте почту или запросите новое письмо.'
    #     )
    #     return redirect('accounts:resend_verification')
    
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


def game_listings(request, slug):
    """Объявления конкретной игры с оптимизацией запросов."""
    game = get_object_or_404(Game, slug=slug, is_active=True)
    
    # Оптимизация: добавляем profile для seller
    listings = Listing.objects.filter(
        game=game,
        status='active'
    ).select_related('seller', 'seller__profile', 'category')\
     .order_by('-created_at')
    
    # Получаем категории для фильтрации
    categories = game.categories.filter(is_active=True).order_by('order', 'name')
    
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


@csrf_exempt
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

