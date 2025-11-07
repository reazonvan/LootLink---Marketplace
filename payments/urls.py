from django.urls import path
from . import views
from . import views_disputes

app_name = 'payments'

urlpatterns = [
    # Кошелек
    path('wallet/', views.wallet_dashboard, name='wallet_dashboard'),
    path('wallet/history/', views.transaction_history, name='transaction_history'),
    
    # Пополнение
    path('deposit/', views.deposit, name='deposit'),
    path('deposit/success/', views.deposit_success, name='deposit_success'),
    
    # Вывод
    path('withdrawal/create/', views.withdrawal_create, name='withdrawal_create'),
    
    # Промокоды
    path('promo/apply/', views.apply_promo_code, name='apply_promo_code'),
    
    # Эскроу
    path('escrow/<int:escrow_id>/', views.escrow_detail, name='escrow_detail'),
    
    # Диспуты
    path('disputes/', views_disputes.disputes_list, name='disputes_list'),
    path('dispute/create/<int:escrow_id>/', views_disputes.create_dispute, name='dispute_create'),
    path('dispute/<int:dispute_id>/', views_disputes.dispute_detail, name='dispute_detail'),
    path('dispute/<int:dispute_id>/message/', views_disputes.add_dispute_message, name='dispute_add_message'),
    path('dispute/<int:dispute_id>/moderate/', views_disputes.moderate_dispute, name='dispute_moderate'),
    
    # Webhooks
    path('webhook/yookassa/', views.yookassa_webhook, name='yookassa_webhook'),
]

