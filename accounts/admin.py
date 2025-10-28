from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from .models import CustomUser, Profile, PasswordResetCode, EmailVerification


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """Админка для пользователей с ролями."""
    model = CustomUser
    list_display = ['username', 'email', 'role_display', 'is_verified_display', 'rating_display', 'date_joined']
    list_filter = ['is_staff', 'is_superuser', 'is_active', 'profile__is_verified', 'profile__is_moderator', 'date_joined']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    ordering = ['-date_joined']
    
    def role_display(self, obj):
        """Отображение роли"""
        if obj.is_superuser:
            return format_html('<span style="color: #dc2626; font-weight: bold;">👑 Владелец</span>')
        elif obj.is_staff:
            return format_html('<span style="color: #2563eb; font-weight: bold;">🛡️ Админ</span>')
        elif hasattr(obj, 'profile') and obj.profile.is_moderator:
            return format_html('<span style="color: #059669; font-weight: bold;">⚖️ Модератор</span>')
        elif hasattr(obj, 'profile') and obj.profile.is_verified:
            return format_html('<span style="color: #64748b;">✓ Верифицирован</span>')
        else:
            return format_html('<span style="color: #9ca3af;">👤 Пользователь</span>')
    role_display.short_description = 'Роль'
    
    def is_verified_display(self, obj):
        """Статус верификации"""
        if hasattr(obj, 'profile') and obj.profile.is_verified:
            return format_html('<span style="color: #10b981;">✓</span>')
        return format_html('<span style="color: #ef4444;">✗</span>')
    is_verified_display.short_description = 'Verified'
    
    def rating_display(self, obj):
        """Рейтинг"""
        if hasattr(obj, 'profile'):
            rating = obj.profile.rating
            stars = '⭐' * int(rating)
            return format_html(f'{stars} {rating:.1f}')
        return '-'
    rating_display.short_description = 'Рейтинг'
    
    # Запрет удаления пользователей
    def has_delete_permission(self, request, obj=None):
        return False
    
    # Делаем username и email только для чтения
    def get_readonly_fields(self, request, obj=None):
        if obj:  # Редактирование существующего пользователя
            return self.readonly_fields + ('username', 'email')
        return self.readonly_fields


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'role_badge', 'is_verified', 'is_moderator', 'phone', 'rating', 'total_sales', 'total_purchases']
    list_filter = ['is_verified', 'is_moderator', 'rating']
    search_fields = ['user__username', 'phone']
    list_editable = ['is_verified', 'is_moderator']
    readonly_fields = ['phone', 'total_sales', 'total_purchases', 'rating', 'created_at']
    
    def role_badge(self, obj):
        """Бейдж роли"""
        if obj.user.is_superuser:
            return format_html('<span style="background: #dc2626; color: white; padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: bold;">ВЛАДЕЛЕЦ</span>')
        elif obj.user.is_staff:
            return format_html('<span style="background: #2563eb; color: white; padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: bold;">АДМИН</span>')
        elif obj.is_moderator:
            return format_html('<span style="background: #059669; color: white; padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: bold;">МОДЕРАТОР</span>')
        else:
            return format_html('<span style="background: #9ca3af; color: white; padding: 3px 8px; border-radius: 4px; font-size: 11px;">ПОЛЬЗОВАТЕЛЬ</span>')
    role_badge.short_description = 'Роль'
    
    # Запрет удаления профилей
    def has_delete_permission(self, request, obj=None):
        return False
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('user', 'avatar', 'bio', 'balance')
        }),
        ('Контакты', {
            'fields': ('phone', 'telegram', 'discord')
        }),
        ('Права доступа', {
            'fields': ('is_verified', 'is_moderator', 'verification_date'),
            'description': 'Управление правами пользователя'
        }),
        ('Статистика', {
            'fields': ('rating', 'total_sales', 'total_purchases'),
            'classes': ('collapse',)
        }),
    )


@admin.register(PasswordResetCode)
class PasswordResetCodeAdmin(admin.ModelAdmin):
    list_display = ['user', 'code', 'created_at', 'expires_at', 'is_used']
    list_filter = ['is_used', 'created_at']
    search_fields = ['user__username', 'user__email', 'code']
    readonly_fields = ['created_at']
    ordering = ['-created_at']
    
    def has_add_permission(self, request):
        # Коды создаются автоматически через систему
        return False


@admin.register(EmailVerification)
class EmailVerificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'is_verified', 'created_at', 'verified_at']
    list_filter = ['is_verified', 'created_at']
    search_fields = ['user__username', 'user__email', 'token']
    readonly_fields = ['token', 'created_at', 'verified_at']
    ordering = ['-created_at']
    
    def has_add_permission(self, request):
        # Создаются автоматически при регистрации
        return False

