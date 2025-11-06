from django.urls import path
from . import views
from . import search_views
from . import views_trading

app_name = 'listings'

urlpatterns = [
    path('', views.landing_page, name='home'),
    path('catalog/', views.games_catalog, name='catalog'),  # Каталог игр (как на Funpay)
    path('listing/<int:pk>/', views.listing_detail, name='listing_detail'),
    path('listing/create/', views.listing_create, name='listing_create'),
    path('listing/<int:pk>/edit/', views.listing_edit, name='listing_edit'),
    path('listing/<int:pk>/delete/', views.listing_delete, name='listing_delete'),
    path('listing/<int:pk>/favorite/', views.toggle_favorite, name='toggle_favorite'),
    path('favorites/', views.favorites_list, name='favorites'),
    path('game/<slug:game_slug>/', views.game_listings, name='game_listings'),
    path('game/<slug:game_slug>/category/<slug:category_slug>/', views.category_listings, name='category_listings'),  # Новый URL для категорий
    
    # Жалобы
    path('listing/<int:pk>/report/', views.report_listing, name='report_listing'),
    path('user/<str:username>/report/', views.report_user, name='report_user'),
    
    # Global Search
    path('search/', search_views.global_search, name='global_search'),
    path('search/saved/', search_views.saved_searches, name='saved_searches'),
    path('search/save/', search_views.save_search, name='save_search'),
    path('search/quick-filters/', search_views.quick_filters, name='quick_filters'),
    
    # Trading: Price offers, reservations  
    path('listing/<int:listing_id>/make-offer/', views_trading.make_price_offer, name='make_price_offer'),
    path('listing/<int:listing_id>/reserve/', views_trading.reserve_listing, name='reserve_listing'),
    path('listing/<int:listing_id>/price-history/', views_trading.listing_price_history, name='listing_price_history'),
    path('my-offers/', views_trading.my_price_offers, name='my_price_offers'),
    path('my-reservations/', views_trading.my_reservations, name='my_reservations'),
    path('offer/<int:offer_id>/respond/', views_trading.respond_to_offer, name='respond_to_offer'),
    path('reservation/<int:reservation_id>/cancel/', views_trading.cancel_reservation, name='cancel_reservation'),
    
    # API endpoints
    path('api/categories/', views.get_categories_by_game, name='api_categories'),
]

