"""
Продвинутая система поиска по объявлениям.
"""
from django.shortcuts import render
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from django.db.models import Q, Count, Avg, Min, Max
from django.core.paginator import Paginator
from .models import Listing, Game, Category
from accounts.models import Profile
from decimal import Decimal


def global_search(request):
    """
    Глобальный поиск по всем объявлениям с расширенными фильтрами.
    """
    # Получаем параметры поиска
    search_query = request.GET.get('q', '').strip()
    game_slug = request.GET.get('game', '')
    category_slug = request.GET.get('category', '')
    min_price = request.GET.get('min_price', '')
    max_price = request.GET.get('max_price', '')
    seller_rating = request.GET.get('seller_rating', '')
    verified_only = request.GET.get('verified_only', False)
    sort_by = request.GET.get('sort', '-created_at')
    
    # Базовый queryset
    listings = Listing.objects.filter(status='active').select_related(
        'seller', 'seller__profile', 'game', 'category'
    )
    
    # Полнотекстовый поиск
    if search_query:
        search_vector = SearchVector('title', weight='A', config='russian') + \
                       SearchVector('description', weight='B', config='russian')
        search_q = SearchQuery(search_query, config='russian')
        listings = listings.annotate(
            rank=SearchRank(search_vector, search_q)
        ).filter(
            Q(search_vector=search_q) |
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query)
        ).order_by('-rank', '-created_at')
    
    # Фильтр по игре
    if game_slug:
        listings = listings.filter(game__slug=game_slug)
    
    # Фильтр по категории
    if category_slug:
        listings = listings.filter(category__slug=category_slug)
    
    # Фильтр по цене
    if min_price:
        try:
            listings = listings.filter(price__gte=Decimal(min_price))
        except:
            pass
    
    if max_price:
        try:
            listings = listings.filter(price__lte=Decimal(max_price))
        except:
            pass
    
    # Фильтр по рейтингу продавца
    if seller_rating:
        try:
            min_rating = Decimal(seller_rating)
            listings = listings.filter(seller__profile__rating__gte=min_rating)
        except:
            pass
    
    # Только верифицированные продавцы
    if verified_only:
        listings = listings.filter(seller__profile__is_verified=True)
    
    # Сортировка
    if sort_by == 'price_asc':
        listings = listings.order_by('price', '-created_at')
    elif sort_by == 'price_desc':
        listings = listings.order_by('-price', '-created_at')
    elif sort_by == 'rating':
        listings = listings.order_by('-seller__profile__rating', '-created_at')
    elif sort_by == 'oldest':
        listings = listings.order_by('created_at')
    elif sort_by != '-created_at' and not search_query:
        listings = listings.order_by('-created_at')
    
    # Статистика для фильтров
    price_range = listings.aggregate(
        min_price=Min('price'),
        max_price=Max('price')
    )
    
    # Пагинация
    paginator = Paginator(listings, 24)  # 24 объявления на странице
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Список игр с количеством объявлений
    games_with_count = Game.objects.filter(
        is_active=True,
        listings__status='active'
    ).annotate(
        listing_count=Count('listings')
    ).filter(listing_count__gt=0).order_by('-listing_count')[:20]
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'games': games_with_count,
        'selected_game': game_slug,
        'selected_category': category_slug,
        'min_price': min_price,
        'max_price': max_price,
        'seller_rating': seller_rating,
        'verified_only': verified_only,
        'sort_by': sort_by,
        'price_range': price_range,
        'total_count': paginator.count,
    }
    
    return render(request, 'listings/global_search.html', context)


def saved_searches(request):
    """
    Сохраненные поисковые запросы пользователя.
    """
    if not request.user.is_authenticated:
        return render(request, 'listings/saved_searches.html', {'saved_searches': []})
    
    # Получаем из сессии или модели
    saved_searches = request.session.get('saved_searches', [])
    
    context = {
        'saved_searches': saved_searches
    }
    return render(request, 'listings/saved_searches.html', context)


def save_search(request):
    """
    Сохранить текущий поисковый запрос.
    """
    if request.method == 'POST' and request.user.is_authenticated:
        search_data = {
            'query': request.POST.get('q', ''),
            'game': request.POST.get('game', ''),
            'category': request.POST.get('category', ''),
            'min_price': request.POST.get('min_price', ''),
            'max_price': request.POST.get('max_price', ''),
        }
        
        # Сохраняем в сессии (можно потом перенести в модель)
        saved_searches = request.session.get('saved_searches', [])
        
        # Проверяем, что такого поиска еще нет
        if search_data not in saved_searches:
            saved_searches.insert(0, search_data)
            # Ограничиваем до 10 сохраненных поисков
            saved_searches = saved_searches[:10]
            request.session['saved_searches'] = saved_searches
    
    from django.shortcuts import redirect
    return redirect('listings:global_search')


def quick_filters(request):
    """
    Быстрые фильтры (популярные категории, ценовые диапазоны).
    """
    # Популярные категории
    popular_categories = Category.objects.filter(
        is_active=True,
        listings__status='active'
    ).annotate(
        listing_count=Count('listings')
    ).filter(listing_count__gt=0).order_by('-listing_count')[:10]
    
    # Ценовые диапазоны
    price_ranges = [
        {'min': 0, 'max': 100, 'label': 'До 100 ₽'},
        {'min': 100, 'max': 500, 'label': '100-500 ₽'},
        {'min': 500, 'max': 1000, 'label': '500-1000 ₽'},
        {'min': 1000, 'max': 5000, 'label': '1000-5000 ₽'},
        {'min': 5000, 'max': None, 'label': 'Более 5000 ₽'},
    ]
    
    context = {
        'popular_categories': popular_categories,
        'price_ranges': price_ranges,
    }
    
    return render(request, 'listings/quick_filters.html', context)

