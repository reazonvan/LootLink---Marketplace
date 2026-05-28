"""
API endpoints для админ-панели (AJAX операции)
"""

from datetime import timedelta

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import user_passes_test
from django.db import transaction as db_transaction
from django.db.models import Avg, Count, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.models import CustomUser, Profile
from core.models_audit import SecurityAuditLog
from core.utils import get_client_ip
from listings.models import Listing, Report
from payments.models_disputes import Dispute
from transactions.models import PurchaseRequest


def is_staff_or_moderator(user):
    """Проверка прав"""
    if not user.is_authenticated:
        return False
    if user.is_staff:
        return True
    profile = getattr(user, "profile", None)
    return bool(profile and profile.is_moderator)


def _audit(action_type, *, actor, target=None, description, risk_level, request, **metadata):
    """Унифицированный аудит-лог админ-действий: actor + target_user_id в metadata."""
    md = {"actor_id": actor.id, "actor_username": actor.username}
    if target is not None:
        md["target_user_id"] = target.id
        md["target_username"] = target.username
    md.update(metadata)
    SecurityAuditLog.objects.create(
        user=actor,
        action_type=action_type,
        risk_level=risk_level,
        description=description,
        ip_address=get_client_ip(request),
        user_agent=request.META.get("HTTP_USER_AGENT", "")[:255],
        metadata=md,
    )


def json_response(success=True, message="", data=None):
    """Стандартный JSON ответ"""
    response = {
        "success": success,
        "message": message,
    }
    if data:
        response["data"] = data
    return JsonResponse(response)


# ═══════════════════════════════════════════════════════════════
# ПОЛЬЗОВАТЕЛИ
# ═══════════════════════════════════════════════════════════════


@require_POST
@user_passes_test(is_staff_or_moderator)
def verify_user(request, user_id):
    """Верификация пользователя"""
    user = get_object_or_404(CustomUser, id=user_id)
    profile = user.profile

    profile.is_verified = not profile.is_verified
    profile.save(update_fields=["is_verified"])

    _audit(
        action_type="profile_update",
        actor=request.user,
        target=user,
        description=(
            f'Верификация {"включена" if profile.is_verified else "отключена"} '
            f"администратором {request.user.username}"
        ),
        risk_level="low",
        request=request,
        is_verified=profile.is_verified,
    )

    return json_response(
        success=True,
        message=f'Пользователь {"верифицирован" if profile.is_verified else "снята верификация"}',
        data={"is_verified": profile.is_verified},
    )


@require_POST
@staff_member_required
def ban_user(request, user_id):
    """Блокировка пользователя с инвалидацией всех его сессий.

    P2-10: критическая операция — требуем 2FA через middleware/checker.
    """
    from django_otp.plugins.otp_totp.models import TOTPDevice

    if not TOTPDevice.objects.filter(user=request.user, confirmed=True).exists():
        return json_response(False, "Включите 2FA для критических админ-операций")
    user = get_object_or_404(CustomUser, id=user_id)

    if user.is_superuser:
        return json_response(False, "Нельзя заблокировать владельца")
    if user.pk == request.user.pk:
        return json_response(False, "Нельзя заблокировать самого себя")

    from django.contrib.sessions.models import Session

    with db_transaction.atomic():
        user.is_active = False
        user.save(update_fields=["is_active"])

        # A1: Инвалидируем сессии стримом (см. accounts.models.CustomUser.delete).
        terminated_sessions = 0
        user_id_str = str(user.pk)
        sessions_qs = Session.objects.filter(expire_date__gte=timezone.now())
        for session in sessions_qs.iterator(chunk_size=500):
            try:
                data = session.get_decoded()
            except Exception:  # nosec B112 — порченная сессия → skip
                continue
            if str(data.get("_auth_user_id")) == user_id_str:
                session.delete()
                terminated_sessions += 1

    _audit(
        action_type="account_locked",
        actor=request.user,
        target=user,
        description=f"Пользователь {user.username} заблокирован",
        risk_level="high",
        request=request,
        terminated_sessions=terminated_sessions,
    )

    return json_response(True, "Пользователь заблокирован")


@require_POST
@staff_member_required
def unban_user(request, user_id):
    """Разблокировка пользователя"""
    user = get_object_or_404(CustomUser, id=user_id)

    user.is_active = True
    user.save(update_fields=["is_active"])

    _audit(
        action_type="account_unlocked",
        actor=request.user,
        target=user,
        description=f"Пользователь {user.username} разблокирован",
        risk_level="low",
        request=request,
    )

    return json_response(True, "Пользователь разблокирован")


@require_POST
@staff_member_required
def toggle_moderator(request, user_id):
    """Назначить/снять модератора"""
    user = get_object_or_404(CustomUser, id=user_id)
    profile = user.profile

    profile.is_moderator = not profile.is_moderator
    profile.save(update_fields=["is_moderator"])

    _audit(
        action_type="profile_update",
        actor=request.user,
        target=user,
        description=(f'Статус модератора {"назначен" if profile.is_moderator else "снят"}'),
        risk_level="medium",
        request=request,
        is_moderator=profile.is_moderator,
    )

    return json_response(
        success=True,
        message=f'Пользователь {"назначен модератором" if profile.is_moderator else "снят с модерации"}',
        data={"is_moderator": profile.is_moderator},
    )


# ═══════════════════════════════════════════════════════════════
# ОБЪЯВЛЕНИЯ
# ═══════════════════════════════════════════════════════════════


@require_POST
@user_passes_test(is_staff_or_moderator)
def approve_listing(request, listing_id):
    """Одобрить объявление (только из cancelled/rejected → active)."""
    listing = get_object_or_404(Listing, id=listing_id)

    if listing.status in ("sold", "reserved"):
        return json_response(False, "Нельзя одобрить проданное/зарезервированное объявление")

    listing.status = "active"
    listing.save(update_fields=["status"])

    _audit(
        action_type="listing_edit",
        actor=request.user,
        target=listing.seller,
        description=f'Объявление "{listing.title}" одобрено модератором',
        risk_level="low",
        request=request,
        listing_id=listing.id,
    )

    return json_response(True, "Объявление одобрено и опубликовано")


@require_POST
@user_passes_test(is_staff_or_moderator)
def reject_listing(request, listing_id):
    """Отклонить объявление (active → cancelled)."""
    listing = get_object_or_404(Listing, id=listing_id)
    reason = (request.POST.get("reason", "") or "")[:500]

    if listing.status not in ("active", "reserved"):
        return json_response(False, f"Нельзя отклонить объявление в статусе {listing.status}")

    listing.status = "cancelled"
    listing.save(update_fields=["status"])

    _audit(
        action_type="listing_edit",
        actor=request.user,
        target=listing.seller,
        description=f'Объявление "{listing.title}" отклонено модератором. Причина: {reason}',
        risk_level="medium",
        request=request,
        listing_id=listing.id,
        reason=reason,
    )

    return json_response(True, "Объявление отклонено")


@require_POST
@staff_member_required
def delete_listing(request, listing_id):
    """Удалить объявление (soft-delete через cancelled).

    Жёсткое удаление запрещено — оно бы каскадно убило PurchaseRequest и
    Escrow с замороженными деньгами. Для деактивации используем cancelled.
    P2-10: требуем 2FA для критической операции.
    """
    from django_otp.plugins.otp_totp.models import TOTPDevice

    if not TOTPDevice.objects.filter(user=request.user, confirmed=True).exists():
        return json_response(False, "Включите 2FA для критических админ-операций")
    listing = get_object_or_404(Listing, id=listing_id)
    title = listing.title
    seller = listing.seller

    # Проверка: нельзя «удалять» листинг с funded эскроу или активными запросами
    if listing.purchase_requests.filter(status__in=["pending", "accepted"]).exists():
        return json_response(
            False,
            "Нельзя удалить объявление с активными запросами. "
            "Сначала разрешите все споры/сделки.",
        )

    listing.status = "cancelled"
    listing.save(update_fields=["status"])

    _audit(
        action_type="listing_delete",
        actor=request.user,
        target=seller,
        description=f'Объявление "{title}" деактивировано администратором',
        risk_level="high",
        request=request,
        listing_id=listing.id,
    )

    return json_response(True, "Объявление деактивировано")


# ═══════════════════════════════════════════════════════════════
# ТРАНЗАКЦИИ
# ═══════════════════════════════════════════════════════════════


@require_POST
@staff_member_required
def cancel_transaction(request, transaction_id):
    """Отменить транзакцию (только админ) с возвратом эскроу покупателю.

    P2-10: финансовая операция — требуем 2FA.
    """
    from django_otp.plugins.otp_totp.models import TOTPDevice

    if not TOTPDevice.objects.filter(user=request.user, confirmed=True).exists():
        return json_response(False, "Включите 2FA для критических админ-операций")
    pr = get_object_or_404(PurchaseRequest, id=transaction_id)
    reason = (request.POST.get("reason") or "Отменено администратором")[:500]

    if pr.status == "completed":
        return json_response(False, "Нельзя отменить завершенную сделку")
    if pr.status in ("cancelled", "rejected"):
        return json_response(False, f"Сделка уже в статусе {pr.status}")

    with db_transaction.atomic():
        pr_locked = PurchaseRequest.objects.select_for_update().get(pk=pr.pk)

        # Возвращаем эскроу покупателю, если был funded
        escrow = getattr(pr_locked, "escrow", None)
        refunded = False
        if escrow is not None and escrow.status == "funded":
            escrow.refund_to_buyer(reason=f"Отмена администратором: {reason}")
            refunded = True

        pr_locked.status = "cancelled"
        pr_locked.cancelled_at = timezone.now()
        pr_locked.save(update_fields=["status", "cancelled_at"])

        # Возвращаем листинг в активные, если он был зарезервирован
        if pr_locked.listing.status == "reserved":
            pr_locked.listing.status = "active"
            pr_locked.listing.save(update_fields=["status"])

    _audit(
        action_type="purchase_complete",
        actor=request.user,
        target=pr.buyer,
        description=f"Транзакция #{pr.id} отменена администратором. Причина: {reason}",
        risk_level="high",
        request=request,
        purchase_request_id=pr.id,
        escrow_refunded=refunded,
        reason=reason,
    )

    return json_response(True, "Транзакция отменена" + (" с возвратом эскроу" if refunded else ""))


# ═══════════════════════════════════════════════════════════════
# СПОРЫ
# ═══════════════════════════════════════════════════════════════


@require_POST
@staff_member_required
def resolve_dispute(request, dispute_id):  # noqa: C901
    """Разрешить спор: вызывает корректный метод модели Dispute.

    Параметры POST:
        winner: 'buyer' | 'seller' | 'partial'
        resolution: текстовое решение модератора
        refund_amount: (только для winner=partial) сумма возврата покупателю

    P2-10: финансовая операция — требуем 2FA.
    """
    from decimal import Decimal, InvalidOperation

    from django_otp.plugins.otp_totp.models import TOTPDevice

    if not TOTPDevice.objects.filter(user=request.user, confirmed=True).exists():
        return json_response(False, "Включите 2FA для критических админ-операций")

    dispute = get_object_or_404(Dispute.objects.select_related("escrow"), id=dispute_id)
    resolution = (request.POST.get("resolution") or "").strip()
    winner = request.POST.get("winner")

    if not resolution:
        return json_response(False, "Укажите текст решения")
    if winner not in ("buyer", "seller", "partial"):
        return json_response(False, "winner должен быть buyer|seller|partial")

    if dispute.status in Dispute.RESOLVED_STATUSES:
        return json_response(False, f"Спор уже разрешён ({dispute.status})")

    try:
        if winner == "buyer":
            dispute.resolve_for_buyer(
                decision_text=resolution,
                full_refund=True,
                moderator=request.user,
            )
        elif winner == "seller":
            dispute.resolve_for_seller(decision_text=resolution, moderator=request.user)
        else:  # partial
            raw_amount = request.POST.get("refund_amount")
            if not raw_amount:
                return json_response(False, "Для partial укажите refund_amount")
            try:
                refund_amount = Decimal(str(raw_amount))
            except (InvalidOperation, ValueError):
                return json_response(False, "Некорректная сумма refund_amount")
            dispute.resolve_for_buyer(
                decision_text=resolution,
                full_refund=False,
                refund_amount=refund_amount,
                moderator=request.user,
            )
    except ValueError as exc:
        return json_response(False, str(exc))
    except Exception as exc:  # pragma: no cover
        import logging

        logging.getLogger(__name__).exception("resolve_dispute failed")
        return json_response(False, f"Ошибка: {exc}")

    return json_response(True, "Спор разрешен")


# ═══════════════════════════════════════════════════════════════
# РЕПОРТЫ
# ═══════════════════════════════════════════════════════════════


@require_POST
@user_passes_test(is_staff_or_moderator)
def process_report(request, report_id):
    """Обработать жалобу: атомарно меняет статус с проверкой текущего."""
    action = request.POST.get("action")  # 'approve' | 'reject'
    if action not in ("approve", "reject"):
        return json_response(False, "Неверное действие")

    with db_transaction.atomic():
        report = Report.objects.select_for_update().select_related("listing").get(pk=report_id)
        if report.status != "pending":
            return json_response(False, f"Жалоба уже обработана ({report.status})")

        if action == "approve":
            if report.listing_id:
                # Блокируем listing, но только если он ещё не sold
                listing = Listing.objects.select_for_update().get(pk=report.listing_id)
                if listing.status in ("active", "reserved"):
                    listing.status = "cancelled"
                    listing.save(update_fields=["status"])
            report.status = "resolved"
            report.admin_comment = f"Обработано модератором {request.user.username}"
            report.resolved_at = timezone.now()
            report.save(update_fields=["status", "admin_comment", "resolved_at"])
            message = "Жалоба обоснована, объявление заблокировано"
        else:
            report.status = "rejected"
            report.admin_comment = f"Отклонено модератором {request.user.username}"
            report.resolved_at = timezone.now()
            report.save(update_fields=["status", "admin_comment", "resolved_at"])
            message = "Жалоба отклонена"

    _audit(
        action_type="report_create",
        actor=request.user,
        target=report.reporter,
        description=f"Жалоба #{report.id} {action}ed модератором",
        risk_level="medium",
        request=request,
        report_id=report.id,
        action=action,
    )

    return json_response(True, message)


# ═══════════════════════════════════════════════════════════════
# СТАТИСТИКА
# ═══════════════════════════════════════════════════════════════


@user_passes_test(is_staff_or_moderator)
def get_stats(request):
    """Статистика для графиков.

    P2-2: было N count'ов в цикле (для 30 дней — 90 запросов).
    Теперь — один запрос с TruncDate на каждую метрику.
    """
    from django.db.models.functions import TruncDate

    period = request.GET.get("period", "7")
    try:
        days = max(1, min(int(period), 365))
    except ValueError:
        days = 7

    today = timezone.now().date()
    start_date = today - timedelta(days=days - 1)

    def _aggregate_per_day(queryset, date_field):
        rows = queryset.annotate(d=TruncDate(date_field)).values("d").annotate(c=Count("id"))
        return {row["d"]: row["c"] for row in rows}

    reg_map = _aggregate_per_day(
        CustomUser.objects.filter(date_joined__date__gte=start_date),
        "date_joined",
    )
    list_map = _aggregate_per_day(
        Listing.objects.filter(created_at__date__gte=start_date),
        "created_at",
    )
    tx_map = _aggregate_per_day(
        PurchaseRequest.objects.filter(created_at__date__gte=start_date, status="completed"),
        "created_at",
    )

    registrations, listings, transactions = [], [], []
    for i in range(days):
        d = start_date + timedelta(days=i)
        label = d.strftime("%d.%m")
        registrations.append({"date": label, "count": reg_map.get(d, 0)})
        listings.append({"date": label, "count": list_map.get(d, 0)})
        transactions.append({"date": label, "count": tx_map.get(d, 0)})

    return json_response(
        success=True,
        data={
            "registrations": registrations,
            "listings": listings,
            "transactions": transactions,
        },
    )
