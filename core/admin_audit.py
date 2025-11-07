"""
Admin интерфейс для аудита безопасности.
"""
from django.contrib import admin
from django.utils.html import format_html
from .models_audit import SecurityAuditLog, DataChangeLog


@admin.register(SecurityAuditLog)
class SecurityAuditLogAdmin(admin.ModelAdmin):
    """
    Admin для логов аудита безопасности.
    """
    list_display = [
        'id', 'created_at', 'colored_risk_level', 'user_link', 
        'action_type_display', 'ip_address', 'short_description'
    ]
    list_filter = ['risk_level', 'action_type', 'created_at']
    search_fields = ['user__username', 'ip_address', 'description', 'user_agent']
    readonly_fields = [
        'user', 'action_type', 'risk_level', 'description', 
        'metadata', 'ip_address', 'user_agent', 'created_at'
    ]
    date_hierarchy = 'created_at'
    list_per_page = 50
    ordering = ['-created_at']
    
    def has_add_permission(self, request):
        """Запрещаем ручное создание логов."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Запрещаем изменение логов."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Только superuser может удалять логи."""
        return request.user.is_superuser
    
    def colored_risk_level(self, obj):
        """Цветной индикатор уровня риска."""
        colors = {
            'low': 'green',
            'medium': 'orange',
            'high': 'red',
            'critical': 'darkred'
        }
        color = colors.get(obj.risk_level, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_risk_level_display().upper()
        )
    colored_risk_level.short_description = 'Risk Level'
    
    def user_link(self, obj):
        """Ссылка на пользователя."""
        if obj.user:
            return format_html(
                '<a href="/admin/accounts/customuser/{}/change/">{}</a>',
                obj.user.id,
                obj.user.username
            )
        return '-'
    user_link.short_description = 'User'
    
    def action_type_display(self, obj):
        """Человекочитаемый тип действия."""
        return obj.get_action_type_display()
    action_type_display.short_description = 'Action'
    
    def short_description(self, obj):
        """Короткое описание."""
        if len(obj.description) > 100:
            return obj.description[:100] + '...'
        return obj.description
    short_description.short_description = 'Description'


@admin.register(DataChangeLog)
class DataChangeLogAdmin(admin.ModelAdmin):
    """
    Admin для логов изменения данных.
    """
    list_display = [
        'id', 'created_at', 'model_name', 'object_id', 
        'field_name', 'changed_by_link', 'change_summary'
    ]
    list_filter = ['model_name', 'created_at']
    search_fields = ['model_name', 'field_name', 'old_value', 'new_value', 'changed_by__username']
    readonly_fields = [
        'model_name', 'object_id', 'field_name', 
        'old_value', 'new_value', 'changed_by', 'created_at'
    ]
    date_hierarchy = 'created_at'
    list_per_page = 50
    ordering = ['-created_at']
    
    def has_add_permission(self, request):
        """Запрещаем ручное создание логов."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Запрещаем изменение логов."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Только superuser может удалять логи."""
        return request.user.is_superuser
    
    def changed_by_link(self, obj):
        """Ссылка на пользователя."""
        if obj.changed_by:
            return format_html(
                '<a href="/admin/accounts/customuser/{}/change/">{}</a>',
                obj.changed_by.id,
                obj.changed_by.username
            )
        return '-'
    changed_by_link.short_description = 'Changed By'
    
    def change_summary(self, obj):
        """Краткое описание изменения."""
        old = obj.old_value[:30] + '...' if len(obj.old_value) > 30 else obj.old_value
        new = obj.new_value[:30] + '...' if len(obj.new_value) > 30 else obj.new_value
        return format_html(
            '<span style="color: red;">{}</span> → <span style="color: green;">{}</span>',
            old or '(empty)',
            new or '(empty)'
        )
    change_summary.short_description = 'Change'

