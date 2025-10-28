from django.urls import path
from . import views

app_name = 'listings'

urlpatterns = [
    path('', views.landing_page, name='home'),
    path('catalog/', views.catalog, name='catalog'),
    path('listing/<int:pk>/', views.listing_detail, name='listing_detail'),
    path('listing/create/', views.listing_create, name='listing_create'),
    path('listing/<int:pk>/edit/', views.listing_edit, name='listing_edit'),
    path('listing/<int:pk>/delete/', views.listing_delete, name='listing_delete'),
    path('listing/<int:pk>/favorite/', views.toggle_favorite, name='toggle_favorite'),
    path('favorites/', views.favorites_list, name='favorites'),
    path('game/<slug:slug>/', views.game_listings, name='game_listings'),
    
    # Жалобы
    path('listing/<int:pk>/report/', views.report_listing, name='report_listing'),
    path('user/<str:username>/report/', views.report_user, name='report_user'),
    
    # API endpoints
    path('api/categories/', views.get_categories_by_game, name='api_categories'),
]

