from django.contrib import admin
from .models import Listing, Game, Favorite, Report


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = ['title', 'game', 'seller', 'price', 'status', 'favorites_count', 'created_at']
    list_filter = ['status', 'game', 'created_at']
    search_fields = ['title', 'description', 'seller__username']
    list_editable = ['status']
    readonly_fields = ['created_at', 'updated_at', 'favorites_count']
    
    def favorites_count(self, obj):
        return obj.favorited_by.count()
    favorites_count.short_description = 'В избранном'
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('title', 'game', 'seller', 'description', 'price')
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

