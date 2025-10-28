from django.contrib import admin
from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """Административная панель для уведомлений."""
    
    list_display = ['title', 'user', 'notification_type', 'is_read', 'created_at']
    list_filter = ['notification_type', 'is_read', 'created_at']
    search_fields = ['title', 'message', 'user__username']
    readonly_fields = ['created_at', 'read_at']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('user', 'notification_type', 'title', 'message', 'link')
        }),
        ('Статус', {
            'fields': ('is_read', 'created_at', 'read_at')
        }),
    )
    
    def has_add_permission(self, request):
        """Запрещаем создавать уведомления вручную."""
        return False

