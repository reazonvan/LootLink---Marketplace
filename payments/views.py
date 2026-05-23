import json
import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from . import selectors, services
from .forms import DepositForm, PromoCodeForm, WithdrawalForm
from .models import Escrow, Transaction
from .services import InsufficientFundsError
from .yookassa_integration import yookassa_service

logger = logging.getLogger(__name__)


def _get_client_ip(request):
    from core.utils import get_client_ip

    return get_client_ip(request)


@login_required
def wallet_dashboard(request):
    """Дашборд кошелька пользователя."""
    wallet = selectors.get_or_create_user_wallet(user=request.user)
    context = {
        "wallet": wallet,
        "transactions": selectors.user_recent_transactions(user=request.user, limit=20),
        "active_escrows": selectors.user_active_escrows(user=request.user),
        "pending_withdrawals": selectors.user_pending_withdrawals(user=request.user),
    }
    return render(request, "payments/wallet_dashboard.html", context)


@login_required
def deposit(request):
    """Пополнение баланса."""
    if request.method == "POST":
        form = DepositForm(request.POST)
        if form.is_valid():
            amount = form.cleaned_data["final_amount"]
            return_url = request.build_absolute_uri(reverse("payments:deposit_success"))

            result = services.create_deposit_payment(
                user=request.user,
                amount=amount,
                return_url=return_url,
            )

            if result.get("success"):
                return redirect(result["confirmation_url"])
            messages.error(request, f'Ошибка создания платежа: {result.get("error")}')
    else:
        form = DepositForm()

    return render(request, "payments/deposit.html", {"form": form})


@login_required
def deposit_success(request):
    """Возврат после оплаты. Реальное зачисление происходит через webhook."""
    messages.info(
        request,
        "Платёж обрабатывается. Баланс будет пополнен автоматически в течение нескольких минут.",
    )
    return redirect("payments:wallet_dashboard")


@login_required
def withdrawal_create(request):
    """Создание заявки на вывод средств."""
    wallet = selectors.get_or_create_user_wallet(user=request.user)

    if request.method == "POST":
        form = WithdrawalForm(user=request.user, data=request.POST)
        if form.is_valid():
            try:
                services.create_withdrawal(
                    user=request.user,
                    amount=form.cleaned_data["amount"],
                    payment_method=form.cleaned_data["payment_method"],
                    payment_details=form.cleaned_data["payment_details"],
                )
            except InsufficientFundsError:
                messages.error(request, "Недостаточно средств на балансе.")
                return redirect("payments:withdrawal_create")
            except Exception:
                # Финансовая транзакция — обязательно логируем для аудита.
                logger.exception(
                    "Withdrawal creation failed for user_id=%s",
                    request.user.pk,
                )
                messages.error(request, "Ошибка при создании заявки. Попробуйте позже.")
                return redirect("payments:withdrawal_create")

            messages.success(
                request,
                "Заявка на вывод средств создана. Ожидайте обработки администратором.",
            )
            return redirect("payments:wallet_dashboard")
    else:
        form = WithdrawalForm(user=request.user)

    context = {
        "form": form,
        "wallet": wallet,
        "available_balance": wallet.get_available_balance(),
    }
    return render(request, "payments/withdrawal_create.html", context)


@login_required
@require_http_methods(["POST"])
def apply_promo_code(request):
    """Применить промокод (AJAX)."""
    form = PromoCodeForm(request.POST)
    if form.is_valid():
        promo_code = form.promo_code

        # Сохраняем промокод в сессии
        request.session["promo_code"] = promo_code.code

        return JsonResponse(
            {
                "success": True,
                "message": f'Промокод применен! Скидка: {promo_code.discount_value}{"%" if promo_code.discount_type == "percent" else "₽"}',
                "discount_type": promo_code.discount_type,
                "discount_value": float(promo_code.discount_value),
            }
        )
    return JsonResponse(
        {
            "success": False,
            "errors": form.errors,
        },
        status=400,
    )


@csrf_exempt
@require_http_methods(["POST"])
def yookassa_webhook(request):
    """
    Webhook от ЮKassa с многоуровневой защитой:
        1. IP whitelist (если настроен YOOKASSA_WEBHOOK_ALLOWED_IPS)
        2. Опциональная HMAC-подпись через YOOKASSA_WEBHOOK_SECRET
        3. Сверка с API YooKassa в _verify_webhook_payload (статус/сумма)

    Защита от replay/forgery: даже без HMAC секрета webhook проходит
    верификацию через API (двусторонний trust).
    """
    from django.conf import settings as django_settings

    try:
        request_ip = _get_client_ip(request)

        if (
            yookassa_service.allowed_webhook_ips
            and request_ip not in yookassa_service.allowed_webhook_ips
        ):
            logger.warning(f"Webhook отклонён: недоверенный IP {request_ip}")
            return HttpResponse(status=403)

        body = request.body
        # HMAC верификация, если задан секрет.
        # YooKassa может отправлять подпись в заголовке X-Yookassa-Signature
        # или похожем; формат специфичный — здесь общий шаблон.
        webhook_secret = getattr(django_settings, "YOOKASSA_WEBHOOK_SECRET", "")
        if webhook_secret:
            import hashlib
            import hmac

            signature = (
                request.headers.get("X-Yookassa-Signature")
                or request.headers.get("X-Signature")
                or ""
            )
            expected = hmac.new(
                webhook_secret.encode("utf-8"),
                body,
                hashlib.sha256,
            ).hexdigest()
            if not signature or not hmac.compare_digest(expected, signature):
                logger.warning("Webhook отклонён: неверная HMAC-подпись (ip=%s)", request_ip)
                return HttpResponse(status=403)

        webhook_data = json.loads(body.decode("utf-8"))
        logger.info(
            "Получен webhook от ЮKassa: ip=%s, event=%s",
            request_ip,
            webhook_data.get("event"),
        )

        success = yookassa_service.handle_webhook(webhook_data, request_ip=request_ip)

        if success:
            return HttpResponse(status=200)
        return HttpResponse(status=400)

    except json.JSONDecodeError:
        return HttpResponse(status=400)
    except Exception as e:
        logger.error(f"Ошибка обработки webhook: {str(e)}")
        return HttpResponse(status=500)


@login_required
def transaction_history(request):
    """История транзакций."""
    from django.core.paginator import Paginator

    transactions = selectors.user_transactions(
        user=request.user,
        transaction_type=request.GET.get("type") or None,
        status=request.GET.get("status") or None,
    )

    paginator = Paginator(transactions, 20)
    page_obj = paginator.get_page(request.GET.get("page"))

    context = {
        "transactions": page_obj,
        "page_obj": page_obj,
        "transaction_types": Transaction.TRANSACTION_TYPES,
        "statuses": Transaction.STATUS_CHOICES,
    }
    return render(request, "payments/transaction_history.html", context)


@login_required
def escrow_detail(request, escrow_id):
    """Детали эскроу."""
    escrow = get_object_or_404(Escrow, id=escrow_id)

    # Проверка прав доступа
    if request.user != escrow.buyer and request.user != escrow.seller:
        messages.error(request, "У вас нет доступа к этому эскроу")
        return redirect("payments:wallet_dashboard")

    return render(request, "payments/escrow_detail.html", {"escrow": escrow})
