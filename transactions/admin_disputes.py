"""
Админ-панель для споров и диспутов.
"""
from django.contrib import admin
from django.utils.html import format_html
from .models_disputes import Dispute, DisputeMessage, DisputeEvidence, GuaranteeService


class DisputeMessageInline(admin.TabularInline):
    model = DisputeMessage
    extra = 0
    readonly_fields = ['sender', 'message', 'created_at']
    can_delete = False


class DisputeEvidenceInline(admin.TabularInline):
    model = DisputeEvidence
    extra = 0
    readonly_fields = ['uploader', 'file', 'description', 'uploaded_at']
    can_delete = False


@admin.register(Dispute)
class DisputeAdmin(admin.ModelAdmin):
    list_display = ['id', 'purchase_request', 'initiator', 'reason', 'status_display', 'moderator', 'created_at']
    list_filter = ['status', 'reason', 'created_at']
    search_fields = ['purchase_request__listing__title', 'initiator__username', 'moderator__username']
    readonly_fields = ['purchase_request', 'initiator', 'created_at', 'resolved_at']
    inlines = [DisputeMessageInline, DisputeEvidenceInline]
    
    fieldsets = (
        ('Информация о споре', {
            'fields': ('purchase_request', 'initiator', 'reason', 'description')
        }),
        ('Статус и решение', {
            'fields': ('status', 'moderator', 'moderator_decision')
        }),
        ('Временные метки', {
            'fields': ('created_at', 'resolved_at')
        }),
    )
    
    actions = ['assign_to_me', 'mark_under_review']
    
    def status_display(self, obj):
        colors = {
            'open': 'red',
            'under_review': 'orange',
            'resolved_buyer': 'green',
            'resolved_seller': 'green',
            'resolved_partial': 'blue',
            'closed': 'gray',
        }
        color = colors.get(obj.status, 'gray')
        return format_html('<span style="color: {}; font-weight: bold;">{}</span>', 
                          color, obj.get_status_display())
    status_display.short_description = 'Статус'
    
    def assign_to_me(self, request, queryset):
        updated = queryset.filter(moderator__isnull=True).update(
            moderator=request.user,
            status='under_review'
        )
        self.message_user(request, f'Назначено {updated} споров')
    assign_to_me.short_description = 'Назначить на меня'
    
    def mark_under_review(self, request, queryset):
        updated = queryset.filter(status='open').update(status='under_review')
        self.message_user(request, f'Отмечено {updated} споров как на рассмотрении')
    mark_under_review.short_description = 'Отметить на рассмотрении'


@admin.register(DisputeMessage)
class DisputeMessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'dispute', 'sender', 'is_moderator_message', 'created_at']
    list_filter = ['is_moderator_message', 'created_at']
    search_fields = ['dispute__id', 'sender__username', 'message']
    readonly_fields = ['dispute', 'sender', 'created_at']


@admin.register(DisputeEvidence)
class DisputeEvidenceAdmin(admin.ModelAdmin):
    list_display = ['id', 'dispute', 'uploader', 'file', 'uploaded_at']
    list_filter = ['uploaded_at']
    search_fields = ['dispute__id', 'uploader__username']
    readonly_fields = ['dispute', 'uploader', 'uploaded_at']


@admin.register(GuaranteeService)
class GuaranteeServiceAdmin(admin.ModelAdmin):
    list_display = ['id', 'purchase_request', 'guarantor', 'fee_percentage', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['purchase_request__listing__title', 'guarantor__username']
    readonly_fields = ['purchase_request', 'created_at', 'completed_at']
    
    fieldsets = (
        ('Информация о гарантии', {
            'fields': ('purchase_request', 'guarantor', 'fee_percentage')
        }),
        ('Статус', {
            'fields': ('status', 'notes')
        }),
        ('Временные метки', {
            'fields': ('created_at', 'completed_at')
        }),
    )

