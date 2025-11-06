from django.urls import path
from . import views

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
    
    # Webhooks
    path('webhook/yookassa/', views.yookassa_webhook, name='yookassa_webhook'),
]

