from django.contrib import admin
from django.utils.html import format_html
from .models import Listing, Game, Category, Favorite, Report
from .models_filters import CategoryFilter, FilterOption, ListingFilterValue
# Импортируем админки фильтров
from . import admin_filters


class CategoryInline(admin.TabularInline):
    """Inline редактор категорий внутри игры"""
    model = Category
    extra = 1
    fields = ['name', 'slug', 'icon', 'order', 'is_active']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'categories_count', 'listings_count', 'is_active', 'order']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ['is_active', 'order']
    inlines = [CategoryInline]
    actions = ['activate_games', 'deactivate_games']
    
    @admin.action(description='✅ Активировать выбранные игры')
    def activate_games(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'Активировано игр: {updated}')
    
    @admin.action(description='❌ Деактивировать выбранные игры')
    def deactivate_games(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'Деактивировано игр: {updated}')
    
    def categories_count(self, obj):
        """Количество категорий"""
        count = obj.categories.filter(is_active=True).count()
        return format_html('<span style="background: #eff6ff; color: #2563eb; padding: 2px 8px; border-radius: 4px; font-weight: bold;">{}</span>', count)
    categories_count.short_description = 'Категорий'
    
    def listings_count(self, obj):
        """Количество объявлений"""
        count = obj.listings.filter(status='active').count()
        if count > 0:
            return format_html('<span style="background: #10b981; color: white; padding: 2px 8px; border-radius: 4px; font-weight: bold;">{}</span>', count)
        return format_html('<span style="color: #9ca3af;">{}</span>', count)
    listings_count.short_description = 'Объявлений'
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'slug', 'description', 'icon')
        }),
        ('Настройки', {
            'fields': ('is_active', 'order')
        }),
    )


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'game', 'icon_display', 'listings_count', 'is_active', 'order']
    list_filter = ['game', 'is_active', 'created_at']
    search_fields = ['name', 'game__name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ['is_active', 'order']
    actions = ['activate_categories', 'deactivate_categories']
    
    @admin.action(description='✅ Активировать выбранные категории')
    def activate_categories(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'Активировано категорий: {updated}')
    
    @admin.action(description='❌ Деактивировать выбранные категории')
    def deactivate_categories(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'Деактивировано категорий: {updated}')
    
    def icon_display(self, obj):
        """Отображение иконки"""
        if obj.icon:
            return format_html('<i class="bi {}"></i> {}', obj.icon, obj.icon)
        return '-'
    icon_display.short_description = 'Иконка'
    
    def listings_count(self, obj):
        """Количество объявлений в категории"""
        count = obj.listings.filter(status='active').count()
        if count > 0:
            return format_html('<span style="background: #10b981; color: white; padding: 2px 8px; border-radius: 4px; font-weight: bold;">{}</span>', count)
        return format_html('<span style="color: #9ca3af;">{}</span>', count)
    listings_count.short_description = 'Объявлений'
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('game', 'name', 'slug', 'description')
        }),
        ('Оформление', {
            'fields': ('icon',),
            'description': 'Используйте иконки Bootstrap Icons: https://icons.getbootstrap.com/'
        }),
        ('Настройки', {
            'fields': ('is_active', 'order')
        }),
    )


@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = ['title', 'game', 'category', 'seller', 'price', 'status', 'favorites_count', 'created_at']
    list_filter = ['status', 'game', 'category', 'created_at']
    search_fields = ['title', 'description', 'seller__username']
    list_editable = ['status']
    readonly_fields = ['created_at', 'updated_at', 'favorites_count']
    
    def favorites_count(self, obj):
        return obj.favorited_by.count()
    favorites_count.short_description = 'В избранном'
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('title', 'game', 'category', 'seller', 'description', 'price')
        }),
        ('Медиа', {
            'fields': ('image',)
        }),
        ('Статус', {
            'fields': ('status',)
        }),
        ('Даты', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ['user', 'listing', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__username', 'listing__title']
    readonly_fields = ['created_at']


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ['report_type', 'reporter', 'reason', 'status', 'created_at']
    list_filter = ['report_type', 'reason', 'status', 'created_at']
    search_fields = ['reporter__username', 'description']
    list_editable = ['status']
    readonly_fields = ['created_at', 'reporter']
    
    fieldsets = (
        ('Информация о жалобе', {
            'fields': ('reporter', 'report_type', 'listing', 'reported_user', 'reason', 'description')
        }),
        ('Обработка', {
            'fields': ('status', 'admin_comment', 'resolved_at')
        }),
        ('Даты', {
            'fields': ('created_at',)
        }),
    )

