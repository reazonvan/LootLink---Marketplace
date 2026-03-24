from django.urls import path
from . import views
from . import verification_views
from . import views_2fa
from . import views_security
from . import views_analytics
from . import views_export
from . import views_push

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
    # Backward-compatible alias for old reverse() calls
    path('resend-verification-email/', views.resend_verification_email, name='resend_verification_email'),
    # Verification flow (email + phone)
    path('verification/status/', verification_views.verification_status, name='verification_status'),
    path('verification/phone/request/', verification_views.phone_verification_request, name='phone_verification_request'),
    path('verification/phone/confirm/', verification_views.phone_verification_confirm, name='phone_verification_confirm'),
    path('verification/document/request/', verification_views.request_document_verification, name='request_document_verification'),
    path('verification/document/upload/', verification_views.document_verification_upload, name='document_verification_upload'),
    path('verification/document/status/', verification_views.document_verification_status, name='document_verification_status'),
    # 2FA (Two-Factor Authentication)
    path('2fa/setup/', views_2fa.setup_2fa, name='setup_2fa'),
    path('2fa/verify/', views_2fa.verify_2fa, name='verify_2fa'),
    path('2fa/disable/', views_2fa.disable_2fa, name='disable_2fa'),
    path('2fa/status/', views_2fa.get_2fa_status, name='2fa_status'),
    # Security center (extended)
    path('security/', views_security.security_settings, name='security_settings'),
    path('security/2fa/enable/', views_security.enable_2fa, name='enable_2fa'),
    path('security/2fa/confirm/', views_security.confirm_2fa, name='confirm_2fa'),
    path('security/2fa/disable/', views_security.disable_2fa, name='disable_2fa_security'),
    path('security/login-history/', views_security.login_history, name='login_history'),
    # Analytics
    path('analytics/', views_analytics.analytics_dashboard, name='analytics_dashboard'),
    path('analytics/export/', views_analytics.export_data, name='export_data'),
    # Data Export (GDPR)
    path('data-export/', views_export.request_data_export, name='data_export'),
    path('data-export/download/<int:export_id>/', views_export.download_data_export, name='download_data_export'),
    # Web Push Notifications
    path('push/subscribe/', views_push.subscribe_push, name='push_subscribe'),
    path('push/unsubscribe/', views_push.unsubscribe_push, name='push_unsubscribe'),
    path('push/vapid-key/', views_push.get_vapid_public_key, name='push_vapid_key'),
    # AJAX endpoints для проверки уникальности
    path('api/check-username/', views.check_username_available, name='check_username'),
    path('api/check-email/', views.check_email_available, name='check_email'),
    path('api/check-phone/', views.check_phone_available, name='check_phone'),
]

