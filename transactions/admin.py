from django.contrib import admin
from .models import PurchaseRequest, Review


@admin.register(PurchaseRequest)
class PurchaseRequestAdmin(admin.ModelAdmin):
    list_display = ['listing', 'buyer', 'seller', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['listing__title', 'buyer__username', 'seller__username']
    readonly_fields = ['created_at', 'updated_at', 'completed_at']
    
    fieldsets = (
        ('Информация о сделке', {
            'fields': ('listing', 'buyer', 'seller', 'status')
        }),
        ('Даты', {
            'fields': ('created_at', 'updated_at', 'completed_at')
        }),
    )


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['purchase_request', 'reviewer', 'reviewed_user', 'rating', 'created_at']
    list_filter = ['rating', 'created_at']
    search_fields = ['reviewer__username', 'reviewed_user__username', 'comment']
    readonly_fields = ['created_at']

