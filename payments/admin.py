from django.contrib import admin
from django.utils.html import format_html
from .models import Wallet, Transaction, Escrow, PromoCode, Withdrawal


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ['user', 'balance', 'frozen_balance', 'available_balance_display', 'updated_at']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['created_at', 'updated_at']
    list_filter = ['created_at']
    
    def available_balance_display(self, obj):
        available = obj.get_available_balance()
        color = 'green' if available > 0 else 'gray'
        return format_html('<span style="color: {};">{} ₽</span>', color, available)
    available_balance_display.short_description = 'Доступно'


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'transaction_type', 'amount_display', 'status', 'created_at']
    list_filter = ['transaction_type', 'status', 'payment_system', 'created_at']
    search_fields = ['user__username', 'payment_id', 'description']
    readonly_fields = ['created_at', 'completed_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('user', 'transaction_type', 'amount', 'status', 'description')
        }),
        ('Связи', {
            'fields': ('purchase_request',)
        }),
        ('Платежная система', {
            'fields': ('payment_system', 'payment_id', 'payment_data')
        }),
        ('Временные метки', {
            'fields': ('created_at', 'completed_at')
        }),
    )
    
    def amount_display(self, obj):
        color = 'green' if obj.amount >= 0 else 'red'
        return format_html('<span style="color: {};">{} ₽</span>', color, obj.amount)
    amount_display.short_description = 'Сумма'


@admin.register(Escrow)
class EscrowAdmin(admin.ModelAdmin):
    list_display = ['id', 'buyer', 'seller', 'amount', 'status_display', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['buyer__username', 'seller__username']
    readonly_fields = ['created_at', 'funded_at', 'released_at']
    
    fieldsets = (
        ('Участники', {
            'fields': ('purchase_request', 'buyer', 'seller', 'amount')
        }),
        ('Статус', {
            'fields': ('status', 'auto_release_days', 'release_deadline')
        }),
        ('Временные метки', {
            'fields': ('created_at', 'funded_at', 'released_at')
        }),
    )
    
    def status_display(self, obj):
        colors = {
            'created': 'gray',
            'funded': 'blue',
            'released': 'green',
            'refunded': 'orange',
            'disputed': 'red',
        }
        color = colors.get(obj.status, 'gray')
        return format_html('<span style="color: {};">{}</span>', color, obj.get_status_display())
    status_display.short_description = 'Статус'


@admin.register(PromoCode)
class PromoCodeAdmin(admin.ModelAdmin):
    list_display = ['code', 'discount_display', 'uses_display', 'validity_display', 'is_active']
    list_filter = ['discount_type', 'is_active', 'created_at']
    search_fields = ['code']
    readonly_fields = ['uses_count', 'created_at']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('code', 'discount_type', 'discount_value', 'min_purchase_amount')
        }),
        ('Ограничения', {
            'fields': ('max_uses', 'uses_count', 'valid_from', 'valid_until', 'is_active')
        }),
        ('Метаданные', {
            'fields': ('created_at',)
        }),
    )
    
    def discount_display(self, obj):
        if obj.discount_type == 'percent':
            return f'{obj.discount_value}%'
        return f'{obj.discount_value} ₽'
    discount_display.short_description = 'Скидка'
    
    def uses_display(self, obj):
        if obj.max_uses:
            return f'{obj.uses_count} / {obj.max_uses}'
        return f'{obj.uses_count} / ∞'
    uses_display.short_description = 'Использований'
    
    def validity_display(self, obj):
        is_valid = obj.is_valid()
        color = 'green' if is_valid else 'red'
        text = 'Действителен' if is_valid else 'Недействителен'
        return format_html('<span style="color: {};">{}</span>', color, text)
    validity_display.short_description = 'Валидность'


@admin.register(Withdrawal)
class WithdrawalAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'amount', 'payment_method', 'status_display', 'created_at']
    list_filter = ['status', 'payment_method', 'created_at']
    search_fields = ['user__username', 'payment_details']
    readonly_fields = ['created_at', 'processed_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('user', 'amount', 'payment_method', 'payment_details')
        }),
        ('Статус и обработка', {
            'fields': ('status', 'admin_comment')
        }),
        ('Временные метки', {
            'fields': ('created_at', 'processed_at')
        }),
    )
    
    actions = ['approve_withdrawals', 'reject_withdrawals']
    
    def status_display(self, obj):
        colors = {
            'pending': 'orange',
            'processing': 'blue',
            'completed': 'green',
            'rejected': 'red',
        }
        color = colors.get(obj.status, 'gray')
        return format_html('<span style="color: {};">{}</span>', color, obj.get_status_display())
    status_display.short_description = 'Статус'
    
    def approve_withdrawals(self, request, queryset):
        from django.utils import timezone
        updated = queryset.filter(status='pending').update(
            status='completed',
            processed_at=timezone.now()
        )
        self.message_user(request, f'Одобрено {updated} заявок на вывод')
    approve_withdrawals.short_description = 'Одобрить выбранные заявки'
    
    def reject_withdrawals(self, request, queryset):
        from django.utils import timezone
        updated = queryset.filter(status='pending').update(
            status='rejected',
            processed_at=timezone.now()
        )
        self.message_user(request, f'Отклонено {updated} заявок на вывод')
    reject_withdrawals.short_description = 'Отклонить выбранные заявки'

