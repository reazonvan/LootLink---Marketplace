from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from django.utils import timezone
from .models import CustomUser, Profile, PasswordResetCode, EmailVerification, PhoneVerification, DocumentVerification


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
            return format_html('<span style="color: #dc2626; font-weight: bold;">Владелец</span>')
        elif obj.is_staff:
            return format_html('<span style="color: #2563eb; font-weight: bold;">Админ</span>')
        elif hasattr(obj, 'profile') and obj.profile.is_moderator:
            return format_html('<span style="color: #059669; font-weight: bold;">Модератор</span>')
        elif hasattr(obj, 'profile') and obj.profile.is_verified:
            return format_html('<span style="color: #64748b;">Верифицирован</span>')
        else:
            return format_html('<span style="color: #9ca3af;">Пользователь</span>')
    role_display.short_description = 'Роль'

    def is_verified_display(self, obj):
        """Статус верификации"""
        if hasattr(obj, 'profile') and obj.profile.is_verified:
            return format_html('<span style="color: #10b981;">✔</span>')
        return format_html('<span style="color: #ef4444;">✘</span>')
    is_verified_display.short_description = 'Verified'

    def rating_display(self, obj):
        """Рейтинг"""
        if hasattr(obj, 'profile'):
            rating = obj.profile.rating
            stars = '★' * int(rating)
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


@admin.register(PhoneVerification)
class PhoneVerificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone', 'code', 'is_verified', 'attempts', 'created_at', 'expires_at', 'status_badge']
    list_filter = ['is_verified', 'created_at']
    search_fields = ['user__username', 'phone', 'code']
    readonly_fields = ['code', 'created_at', 'verified_at', 'attempts']
    ordering = ['-created_at']

    def status_badge(self, obj):
        """Статус верификации"""
        if obj.is_verified:
            return format_html('<span style="background: #10b981; color: white; padding: 3px 8px; border-radius: 4px; font-size: 11px;">✔ Верифицирован</span>')
        elif timezone.now() > obj.expires_at:
            return format_html('<span style="background: #ef4444; color: white; padding: 3px 8px; border-radius: 4px; font-size: 11px;">⏱ Истек</span>')
        elif obj.attempts >= 5:
            return format_html('<span style="background: #f59e0b; color: white; padding: 3px 8px; border-radius: 4px; font-size: 11px;">⚠ Превышены попытки</span>')
        else:
            return format_html('<span style="background: #3b82f6; color: white; padding: 3px 8px; border-radius: 4px; font-size: 11px;">⏳ Ожидает</span>')
    status_badge.short_description = 'Статус'

    def has_add_permission(self, request):
        return False


@admin.register(DocumentVerification)
class DocumentVerificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'document_type', 'status_badge', 'created_at', 'reviewed_by', 'reviewed_at']
    list_filter = ['status', 'document_type', 'created_at']
    search_fields = ['user__username', 'admin_comment']
    readonly_fields = ['user', 'document_file', 'created_at', 'reviewed_at', 'reviewed_by']
    ordering = ['-created_at']

    fieldsets = (
        ('Информация о документе', {
            'fields': ('user', 'document_type', 'document_file', 'created_at')
        }),
        ('Проверка', {
            'fields': ('status', 'admin_comment', 'reviewed_by', 'reviewed_at')
        }),
    )

    def status_badge(self, obj):
        """Статус проверки"""
        if obj.status == 'approved':
            return format_html('<span style="background: #10b981; color: white; padding: 3px 8px; border-radius: 4px; font-size: 11px;">✔ Одобрено</span>')
        elif obj.status == 'rejected':
            return format_html('<span style="background: #ef4444; color: white; padding: 3px 8px; border-radius: 4px; font-size: 11px;">✘ Отклонено</span>')
        else:
            return format_html('<span style="background: #f59e0b; color: white; padding: 3px 8px; border-radius: 4px; font-size: 11px;">⏳ На проверке</span>')
    status_badge.short_description = 'Статус'

    def get_readonly_fields(self, request, obj=None):
        """Делаем поля только для чтения после создания"""
        if obj:
            return self.readonly_fields + ('status',)
        return self.readonly_fields

    actions = ['approve_documents', 'reject_documents']

    def approve_documents(self, request, queryset):
        """Массовое одобрение документов"""
        count = 0
        for doc in queryset.filter(status='pending'):
            doc.approve(request.user, 'Одобрено администратором')
            count += 1
        self.message_user(request, f'Одобрено документов: {count}')
    approve_documents.short_description = 'Одобрить выбранные документы'

    def reject_documents(self, request, queryset):
        """Массовое отклонение документов"""
        count = 0
        for doc in queryset.filter(status='pending'):
            doc.reject(request.user, 'Отклонено администратором')
            count += 1
        self.message_user(request, f'Отклонено документов: {count}')
    reject_documents.short_description = 'Отклонить выбранные документы'

