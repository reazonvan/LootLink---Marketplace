from django.contrib import admin
from django.utils.html import format_html

from .models import Escrow, PromoCode, Transaction, Wallet, Withdrawal


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ["user", "balance", "frozen_balance", "available_balance_display", "updated_at"]
    search_fields = ["user__username", "user__email"]
    # Финансовые поля только для чтения — изменение баланса должно идти ТОЛЬКО
    # через Transaction/Escrow (атомарно, с audit log). Прямое редактирование
    # из админки нарушает целостность финансовых данных.
    readonly_fields = ["user", "balance", "frozen_balance", "created_at", "updated_at"]
    list_filter = ["created_at"]

    def has_add_permission(self, request):
        # Wallet создаётся сигналом при создании пользователя
        return False

    def has_delete_permission(self, request, obj=None):
        # Удаление кошелька запрещено — только soft-disable через user.is_active
        return False

    def available_balance_display(self, obj):
        available = obj.get_available_balance()
        color = "green" if available > 0 else "gray"
        return format_html('<span style="color: {};">{} ₽</span>', color, available)

    available_balance_display.short_description = "Доступно"


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "transaction_type", "amount_display", "status", "created_at"]
    list_filter = ["transaction_type", "status", "payment_system", "created_at"]
    search_fields = ["user__username", "payment_id", "description"]
    readonly_fields = ["created_at", "completed_at"]
    date_hierarchy = "created_at"

    fieldsets = (
        (
            "Основная информация",
            {"fields": ("user", "transaction_type", "amount", "status", "description")},
        ),
        ("Связи", {"fields": ("purchase_request",)}),
        ("Платежная система", {"fields": ("payment_system", "payment_id", "payment_data")}),
        ("Временные метки", {"fields": ("created_at", "completed_at")}),
    )

    def amount_display(self, obj):
        color = "green" if obj.amount >= 0 else "red"
        return format_html('<span style="color: {};">{} ₽</span>', color, obj.amount)

    amount_display.short_description = "Сумма"


@admin.register(Escrow)
class EscrowAdmin(admin.ModelAdmin):
    list_display = ["id", "buyer", "seller", "amount", "status_display", "created_at"]
    list_filter = ["status", "created_at"]
    search_fields = ["buyer__username", "seller__username"]
    readonly_fields = ["created_at", "funded_at", "released_at"]

    fieldsets = (
        ("Участники", {"fields": ("purchase_request", "buyer", "seller", "amount")}),
        ("Статус", {"fields": ("status", "auto_release_days", "release_deadline")}),
        ("Временные метки", {"fields": ("created_at", "funded_at", "released_at")}),
    )

    def status_display(self, obj):
        colors = {
            "created": "gray",
            "funded": "blue",
            "released": "green",
            "refunded": "orange",
            "disputed": "red",
        }
        color = colors.get(obj.status, "gray")
        return format_html('<span style="color: {};">{}</span>', color, obj.get_status_display())

    status_display.short_description = "Статус"


@admin.register(PromoCode)
class PromoCodeAdmin(admin.ModelAdmin):
    list_display = ["code", "discount_display", "uses_display", "validity_display", "is_active"]
    list_filter = ["discount_type", "is_active", "created_at"]
    search_fields = ["code"]
    readonly_fields = ["uses_count", "created_at"]

    fieldsets = (
        (
            "Основная информация",
            {"fields": ("code", "discount_type", "discount_value", "min_purchase_amount")},
        ),
        (
            "Ограничения",
            {"fields": ("max_uses", "uses_count", "valid_from", "valid_until", "is_active")},
        ),
        ("Метаданные", {"fields": ("created_at",)}),
    )

    def discount_display(self, obj):
        if obj.discount_type == "percent":
            return f"{obj.discount_value}%"
        return f"{obj.discount_value} ₽"

    discount_display.short_description = "Скидка"

    def uses_display(self, obj):
        if obj.max_uses:
            return f"{obj.uses_count} / {obj.max_uses}"
        return f"{obj.uses_count} / ∞"

    uses_display.short_description = "Использований"

    def validity_display(self, obj):
        is_valid = obj.is_valid()
        color = "green" if is_valid else "red"
        text = "Действителен" if is_valid else "Недействителен"
        return format_html('<span style="color: {};">{}</span>', color, text)

    validity_display.short_description = "Валидность"


@admin.register(Withdrawal)
class WithdrawalAdmin(admin.ModelAdmin):
    """Админка Withdrawal с защитой PCI-DSS: реквизиты только в маске.

    Поиск по зашифрованным payment_details бесполезен (random base64),
    поэтому ищем по masked. Расшифровка — отдельным действием/представлением.
    """

    list_display = [
        "id",
        "user",
        "amount",
        "payment_method",
        "payment_details_masked",
        "status_display",
        "created_at",
    ]
    list_filter = ["status", "payment_method", "created_at"]
    search_fields = ["user__username", "payment_details_masked"]
    readonly_fields = ["created_at", "processed_at", "payment_details_masked", "reveal_details"]
    date_hierarchy = "created_at"

    fieldsets = (
        ("Основная информация", {"fields": ("user", "amount", "payment_method")}),
        (
            "Реквизиты (PCI-DSS)",
            {
                "fields": ("payment_details_masked", "reveal_details"),
                "description": "Маскированные реквизиты. Расшифровка — через Reveal-кнопку (action audit log).",
            },
        ),
        ("Статус и обработка", {"fields": ("status", "admin_comment")}),
        ("Временные метки", {"fields": ("created_at", "processed_at")}),
    )

    def reveal_details(self, obj):
        """Кнопка показа расшифрованных реквизитов с audit log.

        В простом виде показываем расшифровку только если установлен флаг
        в сессии (через отдельный action). В минимальной версии — отдадим
        только last4 для безопасности.
        """
        if not obj or not obj.payment_details:
            return "—"
        return format_html(
            "<em>Маска: {}</em><br><small>Для расшифровки используйте Django shell "
            "и audit-log: <code>Withdrawal.objects.get(pk={}).get_payment_details()</code></small>",
            obj.payment_details_masked or "***",
            obj.pk,
        )

    reveal_details.short_description = "Полные реквизиты"

    actions = ["approve_withdrawals", "reject_withdrawals"]

    def status_display(self, obj):
        colors = {
            "pending": "orange",
            "processing": "blue",
            "completed": "green",
            "rejected": "red",
        }
        color = colors.get(obj.status, "gray")
        return format_html('<span style="color: {};">{}</span>', color, obj.get_status_display())

    status_display.short_description = "Статус"

    def approve_withdrawals(self, request, queryset):
        """P0-8: одобрение через сервис, чтобы списать balance и frozen_balance."""
        from .services import InsufficientFundsError, WithdrawalStateError, complete_withdrawal

        ok, fail = 0, 0
        for w in queryset.filter(status__in=["pending", "processing"]):
            try:
                complete_withdrawal(
                    withdrawal_id=w.id,
                    admin_comment=f"Одобрено админом {request.user.username}",
                )
                ok += 1
            except (InsufficientFundsError, WithdrawalStateError) as exc:
                fail += 1
                self.message_user(request, f"#{w.id}: {exc}", level="warning")
        self.message_user(
            request,
            f"Одобрено {ok} заявок, ошибок {fail}",
        )

    approve_withdrawals.short_description = "Одобрить (списать средства)"

    def reject_withdrawals(self, request, queryset):
        """P0-8: отклонение через сервис, чтобы разморозить средства."""
        from .services import WithdrawalStateError, reject_withdrawal

        ok, fail = 0, 0
        for w in queryset.filter(status__in=["pending", "processing"]):
            try:
                reject_withdrawal(
                    withdrawal_id=w.id,
                    admin_comment=f"Отклонено админом {request.user.username}",
                )
                ok += 1
            except WithdrawalStateError as exc:
                fail += 1
                self.message_user(request, f"#{w.id}: {exc}", level="warning")
        self.message_user(
            request,
            f"Отклонено {ok} заявок (средства разморожены), ошибок {fail}",
        )

    reject_withdrawals.short_description = "Отклонить (разморозить средства)"
