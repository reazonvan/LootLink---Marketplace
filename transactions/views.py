import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404, redirect, render

from listings.models import Listing

from . import selectors, services
from .forms import PurchaseRequestForm, ReviewForm
from .models import PurchaseRequest, Review

logger = logging.getLogger(__name__)


@login_required
def purchase_request_create(request, listing_pk):
    """Создание запроса на покупку."""
    listing = get_object_or_404(Listing, pk=listing_pk)

    if request.method == "POST":
        form = PurchaseRequestForm(request.POST)
        if form.is_valid():
            try:
                purchase_request = services.create_purchase_request(
                    listing=listing,
                    buyer=request.user,
                    message=form.cleaned_data.get("message", ""),
                )
            except services.PurchaseRequestStateError as exc:
                logger.info(
                    "purchase_request_create rejected: buyer=%s listing=%s reason=%s",
                    request.user.pk,
                    listing.pk,
                    exc,
                )
                messages.error(request, str(exc))
                # Если уже есть активный запрос — показываем его
                existing = PurchaseRequest.objects.filter(
                    listing=listing,
                    buyer=request.user,
                    status__in=["pending", "accepted"],
                ).first()
                if existing is not None:
                    return redirect("transactions:purchase_request_detail", pk=existing.pk)
                return redirect("listings:listing_detail", pk=listing_pk)

            logger.info(
                "purchase_request created: id=%s buyer=%s seller=%s listing=%s amount=%s",
                purchase_request.pk,
                request.user.pk,
                listing.seller_id,
                listing.pk,
                getattr(purchase_request, "amount", None),
            )
            messages.success(request, "Запрос на покупку отправлен!")
            return redirect("transactions:purchase_request_detail", pk=purchase_request.pk)
    else:
        # GET-запрос: проверяем те же инварианты, что и сервис, но без создания.
        if listing.seller == request.user:
            messages.error(request, "Вы не можете купить свое собственное объявление.")
            return redirect("listings:listing_detail", pk=listing_pk)
        if not listing.is_available():
            messages.error(request, "Это объявление больше не доступно.")
            return redirect("listings:listing_detail", pk=listing_pk)
        existing = PurchaseRequest.objects.filter(
            listing=listing,
            buyer=request.user,
            status__in=["pending", "accepted"],
        ).first()
        if existing is not None:
            messages.info(request, "У вас уже есть активный запрос на это объявление.")
            return redirect("transactions:purchase_request_detail", pk=existing.pk)
        form = PurchaseRequestForm()

    context = {
        "form": form,
        "listing": listing,
    }
    return render(request, "transactions/purchase_request_create.html", context)


@login_required
def purchase_request_detail(request, pk):
    """Детальная информация о запросе на покупку."""
    purchase_request = get_object_or_404(
        PurchaseRequest.objects.select_related("listing", "buyer", "seller"),
        pk=pk,
    )

    # Доступ только для участников сделки
    if request.user not in [purchase_request.buyer, purchase_request.seller]:
        logger.warning(
            "transactions IDOR attempt on pr_detail: user=%s pr=%s buyer=%s seller=%s",
            request.user.pk,
            purchase_request.pk,
            purchase_request.buyer_id,
            purchase_request.seller_id,
        )
        messages.error(request, "У вас нет доступа к этой странице.")
        return redirect("listings:home")

    context = {
        "purchase_request": purchase_request,
        "can_leave_review": selectors.can_user_leave_review(
            purchase_request=purchase_request,
            user=request.user,
        ),
    }
    return render(request, "transactions/purchase_request_detail.html", context)


@login_required
def purchase_request_accept(request, pk):
    """Принятие запроса на покупку (для продавца)."""
    purchase_request = get_object_or_404(PurchaseRequest, pk=pk, seller=request.user)

    if purchase_request.status != "pending":
        messages.error(request, "Этот запрос уже обработан.")
        return redirect("transactions:purchase_request_detail", pk=pk)

    if request.method == "POST":
        try:
            services.accept_purchase_request(request_id=pk, user=request.user)
        except PermissionDenied as exc:
            logger.warning(
                "pr_accept denied: seller=%s pr=%s err=%s",
                request.user.pk,
                pk,
                exc,
            )
            messages.error(request, str(exc) or "Нет прав на это действие.")
            return redirect("transactions:purchase_request_detail", pk=pk)
        except ValidationError as exc:
            logger.info(
                "pr_accept invalid state: seller=%s pr=%s err=%s",
                request.user.pk,
                pk,
                exc,
            )
            messages.error(request, exc.message if hasattr(exc, "message") else str(exc))
            return redirect("transactions:purchase_request_detail", pk=pk)

        logger.info("pr accepted: pr=%s seller=%s", pk, request.user.pk)
        messages.success(request, "Запрос принят! Свяжитесь с покупателем для завершения сделки.")
        return redirect("transactions:purchase_request_detail", pk=pk)

    return render(
        request, "transactions/purchase_request_accept.html", {"purchase_request": purchase_request}
    )


@login_required
def purchase_request_reject(request, pk):
    """Отклонение запроса на покупку (для продавца)."""
    purchase_request = get_object_or_404(PurchaseRequest, pk=pk, seller=request.user)

    if purchase_request.status != "pending":
        messages.error(request, "Этот запрос уже обработан.")
        return redirect("transactions:purchase_request_detail", pk=pk)

    if request.method == "POST":
        try:
            services.reject_purchase_request(request_id=pk, user=request.user)
        except PermissionDenied as exc:
            logger.warning(
                "pr_reject denied: seller=%s pr=%s err=%s",
                request.user.pk,
                pk,
                exc,
            )
            messages.error(request, str(exc) or "Нет прав на это действие.")
            return redirect("transactions:purchase_request_detail", pk=pk)
        except ValidationError as exc:
            logger.info(
                "pr_reject invalid state: seller=%s pr=%s err=%s",
                request.user.pk,
                pk,
                exc,
            )
            messages.error(request, exc.message if hasattr(exc, "message") else str(exc))
            return redirect("transactions:purchase_request_detail", pk=pk)

        logger.info("pr rejected: pr=%s seller=%s", pk, request.user.pk)
        messages.info(request, "Запрос отклонен.")
        return redirect("accounts:my_sales")

    return render(
        request, "transactions/purchase_request_reject.html", {"purchase_request": purchase_request}
    )


@login_required
def purchase_request_complete(request, pk):
    """ОТКЛЮЧЕНО для продавца: средства из эскроу освобождаются только при
    подтверждении покупателем (purchase_request_confirm_received) или через
    auto-release по deadline (Celery payments.auto_release_escrow).

    Продавец больше НЕ может сам забрать деньги — это закрывало бы покупателя
    от защиты эскроу.
    """
    messages.error(
        request,
        "Завершение сделки доступно только покупателю (подтверждение получения) "
        "или администрации. Если покупатель не подтвердил получение в течение "
        "срока эскроу, средства будут переведены автоматически.",
    )
    return redirect("transactions:purchase_request_detail", pk=pk)


@login_required
def purchase_request_confirm_received(request, pk):
    """Подтверждение получения товара покупателем.

    Основной путь завершения сделки в эскроу-flow: покупатель
    подтверждает получение → деньги уходят продавцу.
    """
    purchase_request = get_object_or_404(PurchaseRequest, pk=pk, buyer=request.user)

    if purchase_request.status != "accepted":
        messages.error(
            request,
            "Подтвердить получение можно только после принятия запроса продавцом.",
        )
        return redirect("transactions:purchase_request_detail", pk=pk)

    if request.method == "POST":
        try:
            services.confirm_received_purchase_request(request_id=pk, user=request.user)
        except PermissionDenied as exc:
            logger.warning(
                "pr_confirm_received denied: buyer=%s pr=%s err=%s",
                request.user.pk,
                pk,
                exc,
            )
            messages.error(request, str(exc) or "Нет прав на это действие.")
            return redirect("transactions:purchase_request_detail", pk=pk)
        except ValidationError as exc:
            logger.info(
                "pr_confirm_received invalid: buyer=%s pr=%s err=%s",
                request.user.pk,
                pk,
                exc,
            )
            messages.error(request, exc.message if hasattr(exc, "message") else str(exc))
            return redirect("transactions:purchase_request_detail", pk=pk)

        logger.info(
            "pr received-confirmed: pr=%s buyer=%s (escrow → seller)",
            pk,
            request.user.pk,
        )
        messages.success(
            request,
            "Получение подтверждено! Средства переведены продавцу. Оставьте отзыв.",
        )
        return redirect("transactions:purchase_request_detail", pk=pk)

    return render(
        request,
        "transactions/purchase_request_confirm_received.html",
        {"purchase_request": purchase_request},
    )


@login_required
def purchase_request_cancel(request, pk):
    """Отмена запроса (для покупателя)."""
    purchase_request = get_object_or_404(PurchaseRequest, pk=pk, buyer=request.user)

    if purchase_request.status in ["completed", "cancelled"]:
        messages.error(request, "Этот запрос нельзя отменить.")
        return redirect("transactions:purchase_request_detail", pk=pk)

    if request.method == "POST":
        try:
            services.cancel_purchase_request(request_id=pk, user=request.user)
        except PermissionDenied as exc:
            logger.warning(
                "pr_cancel denied: buyer=%s pr=%s err=%s",
                request.user.pk,
                pk,
                exc,
            )
            messages.error(request, str(exc) or "Нет прав на это действие.")
            return redirect("transactions:purchase_request_detail", pk=pk)
        except ValidationError as exc:
            logger.info(
                "pr_cancel invalid: buyer=%s pr=%s err=%s",
                request.user.pk,
                pk,
                exc,
            )
            messages.error(request, exc.message if hasattr(exc, "message") else str(exc))
            return redirect("transactions:purchase_request_detail", pk=pk)

        logger.info("pr cancelled by buyer: pr=%s buyer=%s", pk, request.user.pk)
        messages.info(request, "Запрос отменен.")
        return redirect("accounts:my_purchases")

    return render(
        request, "transactions/purchase_request_cancel.html", {"purchase_request": purchase_request}
    )


@login_required
def review_create(request, purchase_request_pk):
    """Создание отзыва после завершения сделки."""
    purchase_request = get_object_or_404(PurchaseRequest, pk=purchase_request_pk)

    # Проверки
    if request.user not in [purchase_request.buyer, purchase_request.seller]:
        logger.warning(
            "transactions IDOR attempt on review_create: user=%s pr=%s",
            request.user.pk,
            purchase_request.pk,
        )
        messages.error(request, "У вас нет доступа к этой странице.")
        return redirect("listings:home")

    if purchase_request.status != "completed":
        logger.info(
            "review_create blocked (pr not completed): user=%s pr=%s status=%s",
            request.user.pk,
            purchase_request.pk,
            purchase_request.status,
        )
        messages.error(request, "Отзыв можно оставить только после завершения сделки.")
        return redirect("transactions:purchase_request_detail", pk=purchase_request_pk)

    # Проверяем, не оставлял ли уже отзыв
    if Review.objects.filter(purchase_request=purchase_request, reviewer=request.user).exists():
        logger.info(
            "review_create blocked (already exists): user=%s pr=%s",
            request.user.pk,
            purchase_request.pk,
        )
        messages.info(request, "Вы уже оставили отзыв по этой сделке.")
        return redirect("transactions:purchase_request_detail", pk=purchase_request_pk)

    # Определяем, кого оценивает пользователь
    reviewed_user = (
        purchase_request.seller
        if request.user == purchase_request.buyer
        else purchase_request.buyer
    )

    if request.method == "POST":
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.purchase_request = purchase_request
            review.reviewer = request.user
            review.reviewed_user = reviewed_user
            review.save()
            logger.info(
                "review created: id=%s pr=%s reviewer=%s reviewed=%s rating=%s",
                review.pk,
                purchase_request.pk,
                request.user.pk,
                reviewed_user.pk,
                getattr(review, "rating", None),
            )

            # Создаем уведомление для оцениваемого пользователя через NotificationService
            from core.services import NotificationService

            NotificationService.notify_new_review(review)

            messages.success(request, "Отзыв успешно оставлен!")
            return redirect("accounts:profile", username=reviewed_user.username)
    else:
        form = ReviewForm()

    context = {
        "form": form,
        "purchase_request": purchase_request,
        "reviewed_user": reviewed_user,
    }
    return render(request, "transactions/review_create.html", context)
