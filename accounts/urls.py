from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('profile/<str:username>/', views.profile, name='profile'),
    path('profile-edit/', views.profile_edit, name='profile_edit'),
    path('my-listings/', views.my_listings, name='my_listings'),
    path('my-purchases/', views.my_purchases, name='my_purchases'),
    path('my-sales/', views.my_sales, name='my_sales'),
    path('password-reset/', views.password_reset_request, name='password_reset_request'),
    path('password-reset/confirm/', views.password_reset_confirm, name='password_reset_confirm'),
    # Email верификация
    path('verify-email/<str:token>/', views.verify_email, name='verify_email'),
    path('resend-verification/', views.resend_verification_email, name='resend_verification'),
    # AJAX endpoints для проверки уникальности
    path('api/check-username/', views.check_username_available, name='check_username'),
    path('api/check-email/', views.check_email_available, name='check_email'),
    path('api/check-phone/', views.check_phone_available, name='check_phone'),
]

