"""Views для работы со спорами."""

import logging

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import models
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from payments.models import Escrow
from payments.models_disputes import Dispute, DisputeEvidence, DisputeMessage

from .models import PurchaseRequest

logger = logging.getLogger(__name__)


class DisputeForm(forms.ModelForm):
    """Форма создания спора"""

    class Meta:
        model = Dispute
        fields = ["reason", "description"]
        widgets = {
            "reason": forms.Select(attrs={"class": "form-select"}),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 5,
                    "placeholder": "Подробно опишите проблему...",
                }
            ),
        }


class DisputeMessageForm(forms.ModelForm):
    """Форма отправки сообщения в споре"""

    class Meta:
        model = DisputeMessage
        fields = ["message"]
        widgets = {
            "message": forms.Textarea(
                attrs={"class": "form-control", "rows": 3, "placeholder": "Введите сообщение..."}
            )
        }


DISPUTE_WINDOW_DAYS = 30


def _check_dispute_preconditions(request, purchase_request):
    """Прогоняет 5 префлайт-проверок create_dispute. Возвращает redirect или None."""
    from datetime import timedelta

    from django.utils import timezone

    user_pk = request.user.pk
    pr_pk = purchase_request.pk

    if request.user != purchase_request.buyer and request.user != purchase_request.seller:
        logger.warning(
            "transactions IDOR attempt on create_dispute: user=%s pr=%s",
            user_pk,
            pr_pk,
        )
        messages.error(request, "У вас нет доступа к этой сделке")
        return redirect("listings:home")

    if not hasattr(purchase_request, "escrow"):
        logger.info("create_dispute blocked (no escrow): user=%s pr=%s", user_pk, pr_pk)
        messages.error(request, "Для этой сделки не создан escrow")
        return redirect("transactions:purchase_request_detail", pk=pr_pk)

    if hasattr(purchase_request.escrow, "dispute"):
        logger.info(
            "create_dispute blocked (already exists): user=%s pr=%s dispute=%s",
            user_pk,
            pr_pk,
            purchase_request.escrow.dispute.id,
        )
        messages.info(request, "Спор по этой сделке уже существует")
        return redirect(
            "transactions:dispute_detail", dispute_id=purchase_request.escrow.dispute.id
        )

    if purchase_request.status not in ["accepted", "completed", "disputed"]:
        logger.info(
            "create_dispute blocked (bad pr status): user=%s pr=%s status=%s",
            user_pk,
            pr_pk,
            purchase_request.status,
        )
        messages.error(request, "Спор можно открыть только для принятых или завершенных сделок")
        return redirect("transactions:purchase_request_detail", pk=pr_pk)

    if purchase_request.escrow.status != "funded":
        logger.info(
            "create_dispute blocked (escrow not funded): user=%s pr=%s escrow_status=%s",
            user_pk,
            pr_pk,
            purchase_request.escrow.status,
        )
        messages.error(
            request,
            "Средства уже освобождены/возвращены. Спор по этой сделке невозможен.",
        )
        return redirect("transactions:purchase_request_detail", pk=pr_pk)

    accepted_at = purchase_request.accepted_at or purchase_request.created_at
    if timezone.now() > accepted_at + timedelta(days=DISPUTE_WINDOW_DAYS):
        logger.warning(
            "create_dispute blocked (window expired): user=%s pr=%s accepted_at=%s",
            user_pk,
            pr_pk,
            accepted_at.isoformat(),
        )
        messages.error(
            request,
            f"Срок открытия спора истёк ({DISPUTE_WINDOW_DAYS} дней с момента принятия).",
        )
        return redirect("transactions:purchase_request_detail", pk=pr_pk)

    return None


@login_required
def create_dispute(request, purchase_request_id):
    """Создание спора по сделке.

    P1-14: спор можно открыть только при funded эскроу и не позже
    DISPUTE_WINDOW_DAYS после принятия. Иначе либо нет денег для возврата,
    либо deadline auto-release уже прошёл.
    """
    purchase_request = get_object_or_404(PurchaseRequest, id=purchase_request_id)

    early_redirect = _check_dispute_preconditions(request, purchase_request)
    if early_redirect is not None:
        return early_redirect

    if request.method == "POST":
        form = DisputeForm(request.POST)
        if form.is_valid():
            from django.db import IntegrityError
            from django.db import transaction as db_transaction

            try:
                with db_transaction.atomic():
                    dispute = form.save(commit=False)
                    dispute.escrow = purchase_request.escrow
                    dispute.opened_by = request.user
                    dispute.save()

                    # Помечаем PurchaseRequest как disputed
                    pr_locked = PurchaseRequest.objects.select_for_update().get(
                        pk=purchase_request.pk
                    )
                    pr_locked.status = "disputed"
                    pr_locked.save(update_fields=["status"])

                    # Эскроу тоже отмечаем (reverse OneToOne — escrow без _id)
                    escrow_locked = Escrow.objects.select_for_update().get(
                        pk=purchase_request.escrow.pk
                    )
                    if escrow_locked.status == "funded":
                        escrow_locked.status = "disputed"
                        escrow_locked.save(update_fields=["status"])
            except IntegrityError:
                logger.warning(
                    "create_dispute IntegrityError race: user=%s pr=%s",
                    request.user.pk,
                    purchase_request.pk,
                )
                messages.info(request, "Спор уже был создан.")
                return redirect(
                    "transactions:dispute_detail",
                    dispute_id=purchase_request.escrow.dispute.id,
                )

            logger.warning(
                "dispute opened (transactions): id=%s pr=%s opener=%s reason=%s "
                "buyer=%s seller=%s",
                dispute.id,
                purchase_request.pk,
                request.user.pk,
                dispute.reason,
                purchase_request.buyer_id,
                purchase_request.seller_id,
            )
            messages.success(
                request, "Спор создан. Модератор рассмотрит вашу жалобу в ближайшее время."
            )
            return redirect("transactions:dispute_detail", dispute_id=dispute.id)
    else:
        form = DisputeForm()

    context = {"form": form, "purchase_request": purchase_request}
    return render(request, "transactions/dispute_create.html", context)


@login_required
def dispute_detail(request, dispute_id):
    """Детали спора. Сообщения read-only после resolved/closed."""
    dispute = get_object_or_404(Dispute, id=dispute_id)

    pr = dispute.escrow.purchase_request
    is_moderator = request.user.is_staff or (
        hasattr(request.user, "profile") and request.user.profile.is_moderator
    )
    allowed_users = {dispute.opened_by_id, pr.buyer_id, pr.seller_id, dispute.assigned_to_id}
    if request.user.id not in allowed_users and not is_moderator:
        logger.warning(
            "transactions IDOR attempt on dispute_detail: user=%s dispute=%s",
            request.user.pk,
            dispute.pk,
        )
        messages.error(request, "У вас нет доступа к этому спору")
        return redirect("listings:home")

    is_closed = dispute.status in Dispute.RESOLVED_STATUSES

    if request.method == "POST":
        if is_closed:
            logger.info(
                "dispute message rejected (closed): user=%s dispute=%s status=%s",
                request.user.pk,
                dispute.pk,
                dispute.status,
            )
            messages.error(request, "Спор закрыт — сообщения не принимаются.")
            return redirect("transactions:dispute_detail", dispute_id=dispute_id)
        form = DisputeMessageForm(request.POST)
        if form.is_valid():
            msg = form.save(commit=False)
            msg.dispute = dispute
            msg.sender = request.user
            # is_moderator_message только если реально модератор
            msg.is_moderator_message = is_moderator and request.user.id == (
                dispute.assigned_to_id or (request.user.id if request.user.is_staff else None)
            )
            msg.save()
            logger.info(
                "dispute message (transactions): id=%s dispute=%s sender=%s is_mod=%s",
                msg.id,
                dispute.pk,
                request.user.pk,
                msg.is_moderator_message,
            )

            messages.success(request, "Сообщение отправлено")
            return redirect("transactions:dispute_detail", dispute_id=dispute_id)
    else:
        form = DisputeMessageForm()

    messages_list = dispute.messages.select_related("sender").all()
    evidence = dispute.evidences.select_related("uploaded_by").all()

    context = {
        "dispute": dispute,
        "messages_list": messages_list,
        "evidence": evidence,
        "form": form,
        "is_closed": is_closed,
        "is_moderator": is_moderator,
    }
    return render(request, "transactions/dispute_detail.html", context)


@login_required
def my_disputes(request):
    """Список споров пользователя"""
    # Споры где пользователь - инициатор, покупатель или продавец
    disputes = (
        Dispute.objects.filter(
            models.Q(opened_by=request.user)
            | models.Q(escrow__purchase_request__buyer=request.user)
            | models.Q(escrow__purchase_request__seller=request.user)
        )
        .select_related("escrow__purchase_request", "opened_by", "assigned_to")
        .order_by("-created_at")
    )

    context = {"disputes": disputes}
    return render(request, "transactions/my_disputes.html", context)


@login_required
def upload_evidence(request, dispute_id):
    """Загрузка доказательств с валидацией файла и лимитом количества.

    P1-22: валидация через AttachmentValidator (размер + MIME).
    P2-26: тип доказательства принимается из формы (не всегда screenshot).
    """
    from django.core.exceptions import ValidationError as DjangoValidationError

    from core.validators import AttachmentValidator

    EVIDENCE_LIMIT_PER_USER = 20

    dispute = get_object_or_404(Dispute, id=dispute_id)

    # Только участники могут загружать. Модератор смотрит, но не добавляет.
    pr = dispute.escrow.purchase_request
    if request.user.id not in (pr.buyer_id, pr.seller_id):
        logger.warning(
            "transactions IDOR attempt on upload_evidence: user=%s dispute=%s",
            request.user.pk,
            dispute.pk,
        )
        messages.error(request, "У вас нет прав на загрузку доказательств")
        return redirect("transactions:dispute_detail", dispute_id=dispute_id)

    # Запрещаем загрузку для разрешённых споров (read-only после resolution)
    if dispute.status in Dispute.RESOLVED_STATUSES:
        logger.info(
            "upload_evidence blocked (closed): user=%s dispute=%s status=%s",
            request.user.pk,
            dispute.pk,
            dispute.status,
        )
        messages.error(request, "Спор закрыт, доказательства не принимаются.")
        return redirect("transactions:dispute_detail", dispute_id=dispute_id)

    if request.method == "POST" and request.FILES.get("file"):
        uploaded_file = request.FILES["file"]
        evidence_type = (request.POST.get("evidence_type") or "screenshot").strip()
        if evidence_type not in dict(DisputeEvidence.EVIDENCE_TYPES):
            evidence_type = "screenshot"

        # Лимит количества доказательств от одного юзера в одном споре
        existing_count = DisputeEvidence.objects.filter(
            dispute=dispute, uploaded_by=request.user
        ).count()
        if existing_count >= EVIDENCE_LIMIT_PER_USER:
            logger.warning(
                "upload_evidence rate-limited: user=%s dispute=%s count=%s",
                request.user.pk,
                dispute.pk,
                existing_count,
            )
            messages.error(
                request,
                f"Достигнут лимит доказательств ({EVIDENCE_LIMIT_PER_USER}) на этот спор.",
            )
            return redirect("transactions:dispute_detail", dispute_id=dispute_id)

        # Валидация файла
        try:
            AttachmentValidator(max_size_mb=15)(uploaded_file)
        except DjangoValidationError as exc:
            logger.info(
                "upload_evidence rejected (bad file): user=%s dispute=%s name=%r err=%s",
                request.user.pk,
                dispute.pk,
                getattr(uploaded_file, "name", "?"),
                exc,
            )
            messages.error(request, str(exc))
            return redirect("transactions:dispute_detail", dispute_id=dispute_id)

        ev = DisputeEvidence.objects.create(
            dispute=dispute,
            uploaded_by=request.user,
            evidence_type=evidence_type,
            file=uploaded_file,
            description=(request.POST.get("description", "") or "")[:1000],
        )
        logger.info(
            "evidence uploaded: id=%s dispute=%s by=%s type=%s size=%s",
            ev.id,
            dispute.pk,
            request.user.pk,
            evidence_type,
            getattr(uploaded_file, "size", "?"),
        )
        messages.success(request, "Доказательство загружено")

    return redirect("transactions:dispute_detail", dispute_id=dispute_id)
