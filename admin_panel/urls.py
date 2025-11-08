"""
URL конфигурация кастомной админ-панели
"""
from django.urls import path
from . import views
from . import api_views

app_name = 'admin_panel'

urlpatterns = [
    # Главная страница Dashboard
    path('', views.dashboard, name='dashboard'),
    
    # Управление пользователями
    path('users/', views.users_list, name='users_list'),
    path('users/<int:user_id>/', views.user_detail, name='user_detail'),
    
    # Модерация объявлений
    path('listings/', views.listings_moderation, name='listings_moderation'),
    path('listings/<int:listing_id>/', views.listing_detail, name='listing_detail'),
    
    # Сделки и транзакции
    path('transactions/', views.transactions_list, name='transactions_list'),
    path('transactions/<int:transaction_id>/', views.transaction_detail, name='transaction_detail'),
    
    # Споры
    path('disputes/', views.disputes_list, name='disputes_list'),
    path('disputes/<int:dispute_id>/', views.dispute_detail, name='dispute_detail'),
    
    # Жалобы и репорты
    path('reports/', views.reports_list, name='reports_list'),
    
    # Логи безопасности
    path('security/', views.security_logs, name='security_logs'),
    
    # Настройки
    path('settings/', views.settings, name='settings'),
    
    # ═══════════════════════════════════════════════════════════════
    # API ENDPOINTS - для AJAX операций
    # ═══════════════════════════════════════════════════════════════
    
    # Пользователи
    path('api/users/<int:user_id>/verify/', api_views.verify_user, name='api_verify_user'),
    path('api/users/<int:user_id>/ban/', api_views.ban_user, name='api_ban_user'),
    path('api/users/<int:user_id>/unban/', api_views.unban_user, name='api_unban_user'),
    path('api/users/<int:user_id>/moderator/', api_views.toggle_moderator, name='api_toggle_moderator'),
    
    # Объявления
    path('api/listings/<int:listing_id>/approve/', api_views.approve_listing, name='api_approve_listing'),
    path('api/listings/<int:listing_id>/reject/', api_views.reject_listing, name='api_reject_listing'),
    path('api/listings/<int:listing_id>/delete/', api_views.delete_listing, name='api_delete_listing'),
    
    # Сделки
    path('api/transactions/<int:transaction_id>/cancel/', api_views.cancel_transaction, name='api_cancel_transaction'),
    
    # Споры
    path('api/disputes/<int:dispute_id>/resolve/', api_views.resolve_dispute, name='api_resolve_dispute'),
    
    # Репорты
    path('api/reports/<int:report_id>/process/', api_views.process_report, name='api_process_report'),
    
    # Статистика
    path('api/stats/', api_views.get_stats, name='api_stats'),
]

