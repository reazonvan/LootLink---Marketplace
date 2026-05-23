"""
Бизнес-логика модуля сделок (PurchaseRequest state machine).

HackSoft styleguide:
    - services.py — для всех write/state-change операций.
    - kwargs-only вызовы.
    - Все state-переходы атомарны + select_for_update().
    - Уведомления через NotificationService — после успешного коммита.

State machine (с эскроу-интеграцией):

    pending  ── seller.accept ──▶  accepted (Escrow funded из кошелька buyer)
       │                             │
       │                             ├── buyer.confirm_received ──▶ completed
       │                             │       (Escrow released → seller)
       │                             │
       │                             ├── seller.complete (legacy) ──▶ completed
       │                             │       (Escrow released, если funded)
       │                             │
       │                             └── buyer.dispute ──▶ disputed
       │
       ├── buyer.cancel ──▶ cancelled
       └── seller.reject ──▶ rejected
"""

from __future__ import annotations

import logging

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from listings.models import Listing

from .models import PurchaseRequest

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Доменные исключения
# ---------------------------------------------------------------------------


class PurchaseRequestStateError(ValidationError):
    """Невозможно выполнить переход состояния PurchaseRequest."""


class EscrowFundingError(PurchaseRequestStateError):
    """Не удалось профинансировать эскроу — недостаточно средств у покупателя."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _notify(callable_):
    """
    Запустить уведомление после коммита текущей транзакции.

    Если транзакции нет (вне atomic) — выполнится сразу.
    """
    transaction.on_commit(callable_)


def _get_or_create_escrow(pr):
    """Получить или создать Escrow для PurchaseRequest. Идемпотентно.

    Эскроу фондируется на pr.amount (snapshot цены при создании запроса),
    а НЕ на pr.listing.price — иначе продавец может поднять цену между
    созданием запроса и accept, и покупатель заплатит больше, чем согласился.
    """
    from payments.models import Escrow

    snapshot_amount = pr.amount if pr.amount is not None else pr.listing.price
    escrow, _ = Escrow.objects.get_or_create(
        purchase_request=pr,
        defaults={
            "buyer": pr.buyer,
            "seller": pr.seller,
            "amount": snapshot_amount,
        },
    )
    return escrow


def _try_fund_escrow(escrow):
    """
    Попытаться профинансировать эскроу. Возвращает True/False.

    Не падает наружу — все ожидаемые исключения логируются. Покрывает:
        - ValueError/ValidationError — недостаточно средств,
          неверный статус эскроу;
        - Wallet.DoesNotExist — у покупателя ещё нет кошелька.
    """
    from payments.models import Wallet

    try:
        escrow.fund()
        return True
    except (ValueError, ValidationError, Wallet.DoesNotExist) as exc:
        logger.warning(
            "Escrow fund failed: escrow_id=%s reason=%s",
            escrow.pk,
            str(exc),
        )
        return False


# ---------------------------------------------------------------------------
# Создание запроса
# ---------------------------------------------------------------------------


@transaction.atomic
def create_purchase_request(
    *,
    listing: Listing,
    buyer,
    message: str = "",
) -> PurchaseRequest:
    """
    Создать запрос на покупку.

    Проверяет:
        - покупатель != продавец;
        - объявление доступно (`is_available()`);
        - нет существующего активного запроса (pending/accepted) от этого покупателя.

    Фиксирует цену в PurchaseRequest.amount как snapshot — продавец не
    сможет изменить сумму сделки после создания запроса.

    Raises:
        PurchaseRequestStateError: При нарушении любой из инвариант.
    """
    if listing.seller_id == buyer.pk:
        raise PurchaseRequestStateError("Нельзя купить собственное объявление.")

    # Блокируем листинг — защита от race condition: пока проверяем доступность
    # и создаём запрос, продавец может перевести его в reserved/sold.
    locked_listing = Listing.objects.select_for_update().get(pk=listing.pk)
    if locked_listing.status != "active":
        raise PurchaseRequestStateError("Это объявление больше не доступно.")

    existing = PurchaseRequest.objects.filter(
        listing=locked_listing,
        buyer=buyer,
        status__in=["pending", "accepted"],
    ).first()
    if existing is not None:
        raise PurchaseRequestStateError("У вас уже есть активный запрос на это объявление.")

    pr = PurchaseRequest.objects.create(
        listing=locked_listing,
        buyer=buyer,
        seller=locked_listing.seller,
        amount=locked_listing.price,  # snapshot цены
        message=message,
        status="pending",
    )

    def _on_commit():
        from core.services import NotificationService

        NotificationService.notify_purchase_request(pr)

    _notify(_on_commit)

    logger.info(
        "PurchaseRequest created id=%s listing_id=%s buyer_id=%s",
        pr.pk,
        listing.pk,
        buyer.pk,
    )
    return pr


# ---------------------------------------------------------------------------
# State-переходы
# ---------------------------------------------------------------------------


@transaction.atomic
def accept_purchase_request(*, request_id: int, user) -> PurchaseRequest:
    """
    Принять запрос на покупку (продавец).

    Переход: ``pending -> accepted``. Объявление переходит в ``reserved``.
    Создаётся ``Escrow``, средства покупателя замораживаются на сумму
    листинга. Если средств у покупателя недостаточно — ничего не меняем
    и поднимаем :class:`EscrowFundingError`.

    Выполняется под select_for_update — защита от двойного accept.
    """
    pr = PurchaseRequest.objects.select_for_update().get(pk=request_id)

    if pr.seller_id != user.pk:
        raise PermissionDenied("Только продавец может принять запрос.")
    if pr.status != "pending":
        raise PurchaseRequestStateError("Этот запрос уже обработан.")

    # Создаём эскроу и пытаемся заморозить средства покупателя.
    # Если у покупателя нет кошелька с достаточным балансом —
    # accept не выполняется, транзакция откатывается.
    escrow = _get_or_create_escrow(pr)
    if escrow.status == "created":
        if not _try_fund_escrow(escrow):
            raise EscrowFundingError(
                "Недостаточно средств на кошельке покупателя для оплаты "
                "через эскроу. Покупатель должен пополнить баланс и "
                "создать запрос заново."
            )

    pr.status = "accepted"
    pr.accepted_at = timezone.now()
    pr.save(update_fields=["status", "accepted_at"])

    pr.listing.status = "reserved"
    pr.listing.save(update_fields=["status"])

    def _on_commit():
        from core.services import NotificationService

        NotificationService.notify_request_accepted(pr)

    _notify(_on_commit)

    logger.info(
        "PurchaseRequest accepted id=%s seller_id=%s escrow_id=%s",
        pr.pk,
        user.pk,
        escrow.pk,
    )
    return pr


@transaction.atomic
def reject_purchase_request(*, request_id: int, user) -> PurchaseRequest:
    """Отклонить запрос на покупку (продавец). Переход: ``pending -> rejected``."""
    pr = PurchaseRequest.objects.select_for_update().get(pk=request_id)

    if pr.seller_id != user.pk:
        raise PermissionDenied("Только продавец может отклонить запрос.")
    if pr.status != "pending":
        raise PurchaseRequestStateError("Этот запрос уже обработан.")

    pr.status = "rejected"
    pr.rejected_at = timezone.now()
    pr.save(update_fields=["status", "rejected_at"])

    def _on_commit():
        from core.services import NotificationService

        NotificationService.notify_request_rejected(pr)

    _notify(_on_commit)

    logger.info("PurchaseRequest rejected id=%s seller_id=%s", pr.pk, user.pk)
    return pr


def _finalize_completed_purchase_request(pr) -> None:
    """
    Общая логика финализации сделки: статусы PR/listing, статистика
    профилей, релиз эскроу (если funded). Используется и продавцом
    (legacy complete), и покупателем (confirm_received).
    """
    from django.db.models import F
    from django.utils import timezone

    from accounts.models import Profile

    pr.status = "completed"
    pr.completed_at = timezone.now()
    pr.save(update_fields=["status", "completed_at"])

    pr.listing.status = "sold"
    pr.listing.save(update_fields=["status"])

    Profile.objects.filter(user=pr.seller).update(total_sales=F("total_sales") + 1)
    Profile.objects.filter(user=pr.buyer).update(total_purchases=F("total_purchases") + 1)

    # Если эскроу профинансирован — переводим средства продавцу.
    # release_to_seller сам атомарно блокирует оба кошелька.
    escrow = getattr(pr, "escrow", None)
    if escrow is not None and escrow.status == "funded":
        escrow.release_to_seller()


@transaction.atomic
def complete_purchase_request(*, request_id: int, user) -> PurchaseRequest:
    """
    Завершить сделку (продавец). Переход: ``accepted -> completed``.

    Если эскроу профинансирован — средства автоматически переводятся
    продавцу через ``Escrow.release_to_seller``. Сохранено в качестве
    legacy-API для admin-сценариев и cron-задач; обычный flow —
    :func:`confirm_received_purchase_request` от покупателя.
    """
    pr = PurchaseRequest.objects.select_for_update().get(pk=request_id)

    if pr.seller_id != user.pk:
        raise PermissionDenied("Только продавец может завершить сделку.")
    if pr.status != "accepted":
        raise PurchaseRequestStateError("Сделка должна быть сначала принята.")

    _finalize_completed_purchase_request(pr)

    def _on_commit():
        from core.services import NotificationService

        NotificationService.notify_deal_completed(pr)

    _notify(_on_commit)

    logger.info("PurchaseRequest completed id=%s seller_id=%s", pr.pk, user.pk)
    return pr


@transaction.atomic
def confirm_received_purchase_request(*, request_id: int, user) -> PurchaseRequest:
    """
    Подтверждение получения товара покупателем.

    Переход: ``accepted -> completed``. Если эскроу профинансирован,
    средства автоматически переводятся продавцу. Это основной путь
    завершения сделки в эскроу-flow.
    """
    pr = PurchaseRequest.objects.select_for_update().get(pk=request_id)

    if pr.buyer_id != user.pk:
        raise PermissionDenied("Только покупатель может подтвердить получение.")
    if pr.status != "accepted":
        raise PurchaseRequestStateError(
            "Подтвердить получение можно только после принятия запроса продавцом."
        )

    _finalize_completed_purchase_request(pr)

    def _on_commit():
        from core.services import NotificationService

        NotificationService.notify_deal_completed(pr)

    _notify(_on_commit)

    logger.info("PurchaseRequest confirmed by buyer id=%s buyer_id=%s", pr.pk, user.pk)
    return pr


@transaction.atomic
def cancel_purchase_request(*, request_id: int, user) -> PurchaseRequest:
    """
    Отменить запрос (покупатель).

    Допустимо:
        - в статусе ``pending`` (нет эскроу, простая отмена);
        - в статусе ``accepted`` только если эскроу ещё не профинансирован
          (теоретический случай — практически не наступает).

    После accept с funded escrow — отмена покупателем запрещена;
    остаётся только путь спора (refund возможен по решению модератора).
    """
    pr = PurchaseRequest.objects.select_for_update().get(pk=request_id)

    if pr.buyer_id != user.pk:
        raise PermissionDenied("Только покупатель может отменить запрос.")
    if pr.status in ("completed", "cancelled", "rejected"):
        raise PurchaseRequestStateError("Этот запрос нельзя отменить.")

    # Если эскроу funded — отменять нельзя, нужен спор.
    escrow = getattr(pr, "escrow", None)
    if escrow is not None and escrow.status == "funded":
        raise PurchaseRequestStateError(
            "Деньги уже заморожены в эскроу. Чтобы вернуть средства, "
            "откройте спор — модератор рассмотрит ситуацию."
        )

    pr.status = "cancelled"
    pr.cancelled_at = timezone.now()
    pr.save(update_fields=["status", "cancelled_at"])

    if pr.listing.status == "reserved":
        pr.listing.status = "active"
        pr.listing.save(update_fields=["status"])

    logger.info("PurchaseRequest cancelled id=%s buyer_id=%s", pr.pk, user.pk)
    return pr
