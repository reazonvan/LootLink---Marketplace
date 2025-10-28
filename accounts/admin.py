from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Profile, PasswordResetCode, EmailVerification


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ['username', 'email', 'is_active', 'is_staff', 'date_joined']
    list_filter = ['is_active', 'is_staff', 'date_joined']
    search_fields = ['username', 'email']
    ordering = ['-date_joined']
    
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
    list_display = ['user', 'is_verified', 'phone', 'rating', 'total_sales', 'total_purchases']
    list_filter = ['is_verified', 'rating']
    search_fields = ['user__username', 'phone']
    list_editable = ['is_verified']
    readonly_fields = ['phone', 'total_sales', 'total_purchases', 'rating', 'created_at']
    
    # Запрет удаления профилей
    def has_delete_permission(self, request, obj=None):
        return False
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('user', 'avatar', 'bio')
        }),
        ('Контакты', {
            'fields': ('phone', 'telegram', 'discord')
        }),
        ('Верификация', {
            'fields': ('is_verified', 'verification_date')
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

