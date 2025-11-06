from django.urls import path
from . import views
from . import moderation_views
from . import views_faq

app_name = 'core'

urlpatterns = [
    path('notifications/', views.notifications_list, name='notifications_list'),
    path('notifications/mark-read/<int:pk>/', views.mark_notification_read, name='mark_notification_read'),
    path('notifications/mark-all-read/', views.mark_all_notifications_read, name='mark_all_notifications_read'),
    path('notifications/unread-count/', views.unread_notifications_count, name='unread_notifications_count'),
    
    # Moderation (добавлены выше, но проверим)
    path('moderation/', moderation_views.moderation_dashboard, name='moderation_dashboard'),
    path('moderation/reports/', moderation_views.reports_queue, name='reports_queue'),
    path('moderation/report/<int:report_id>/process/', moderation_views.process_report, name='process_report'),
    path('moderation/bans/', moderation_views.user_bans_list, name='user_bans_list'),
    path('my-reports/', moderation_views.my_reports, name='my_reports'),
    
    # FAQ
    path('faq/', views_faq.faq_page, name='faq'),
    path('faq/<int:faq_id>/helpful/', views_faq.mark_faq_helpful, name='mark_faq_helpful'),
    path('api/templates/<slug:game_slug>/', views_faq.get_templates, name='get_templates'),
]

