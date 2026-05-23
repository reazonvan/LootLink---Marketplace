"""
Админ-панель для споров и диспутов.
"""

from django.contrib import admin
from django.utils.html import format_html

from payments.models_disputes import Dispute, DisputeEvidence, DisputeMessage


class DisputeMessageInline(admin.TabularInline):
    model = DisputeMessage
    extra = 0
    readonly_fields = ["sender", "message", "created_at"]
    can_delete = False


class DisputeEvidenceInline(admin.TabularInline):
    model = DisputeEvidence
    extra = 0
    readonly_fields = ["uploaded_by", "file", "description", "created_at"]
    can_delete = False


@admin.register(Dispute)
class DisputeAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "escrow",
        "opened_by",
        "reason",
        "status_display",
        "assigned_to",
        "created_at",
    ]
    list_filter = ["status", "reason", "created_at"]
    search_fields = [
        "escrow__purchase_request__listing__title",
        "opened_by__username",
        "assigned_to__username",
    ]
    readonly_fields = ["escrow", "opened_by", "created_at", "resolved_at"]
    inlines = [DisputeMessageInline, DisputeEvidenceInline]

    fieldsets = (
        ("Информация о споре", {"fields": ("escrow", "opened_by", "reason", "description")}),
        (
            "Статус и решение",
            {"fields": ("status", "assigned_to", "moderator_decision", "refund_amount")},
        ),
        ("Временные метки", {"fields": ("created_at", "resolved_at")}),
    )

    actions = ["assign_to_me", "mark_under_review"]

    def status_display(self, obj):
        colors = {
            "open": "red",
            "under_review": "orange",
            "resolved_buyer": "green",
            "resolved_seller": "green",
            "resolved_partial": "blue",
            "closed": "gray",
        }
        color = colors.get(obj.status, "gray")
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>', color, obj.get_status_display()
        )

    status_display.short_description = "Статус"

    def assign_to_me(self, request, queryset):
        updated = queryset.filter(assigned_to__isnull=True).update(
            assigned_to=request.user, status="under_review"
        )
        self.message_user(request, f"Назначено {updated} споров")

    assign_to_me.short_description = "Назначить на меня"

    def mark_under_review(self, request, queryset):
        updated = queryset.filter(status="open").update(status="under_review")
        self.message_user(request, f"Отмечено {updated} споров как на рассмотрении")

    mark_under_review.short_description = "Отметить на рассмотрении"


@admin.register(DisputeMessage)
class DisputeMessageAdmin(admin.ModelAdmin):
    list_display = ["id", "dispute", "sender", "is_moderator_message", "created_at"]
    list_filter = ["is_moderator_message", "created_at"]
    search_fields = ["dispute__id", "sender__username", "message"]
    readonly_fields = ["dispute", "sender", "created_at"]


@admin.register(DisputeEvidence)
class DisputeEvidenceAdmin(admin.ModelAdmin):
    list_display = ["id", "dispute", "uploaded_by", "file", "created_at"]
    list_filter = ["created_at"]
    search_fields = ["dispute__id", "uploaded_by__username"]
    readonly_fields = ["dispute", "uploaded_by", "created_at"]
