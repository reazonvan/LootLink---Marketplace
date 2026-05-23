"""
Comprehensive тесты для views приложения transactions.
"""

from decimal import Decimal

from django.urls import reverse

import pytest

from transactions.models import PurchaseRequest, Review


def _fund_buyer_wallet(buyer, amount=Decimal("10000.00")):
    """
    Пополняет кошелёк покупателя для тестов, где accept должен пройти
    через эскроу. Без этого `accept_purchase_request` упадёт с
    EscrowFundingError из-за недостатка средств.
    """
    from payments.models import Wallet

    wallet, _ = Wallet.objects.get_or_create(
        user=buyer,
        defaults={"balance": amount, "frozen_balance": Decimal("0")},
    )
    wallet.balance = amount
    wallet.frozen_balance = Decimal("0")
    wallet.save(update_fields=["balance", "frozen_balance"])
    return wallet


@pytest.mark.django_db
class TestPurchaseRequestCreate:
    """Тесты создания запроса на покупку."""

    def test_create_requires_login(self, client, active_listing):
        """Создание требует авторизации."""
        response = client.get(
            reverse(
                "transactions:purchase_request_create", kwargs={"listing_pk": active_listing.pk}
            )
        )
        assert response.status_code == 302

    def test_cannot_buy_own_listing(self, authenticated_client, verified_user, listing_factory):
        """Нельзя купить свое объявление."""
        listing = listing_factory(verified_user)

        response = authenticated_client.get(
            reverse("transactions:purchase_request_create", kwargs={"listing_pk": listing.pk})
        )

        assert response.status_code == 302

    def test_cannot_buy_unavailable_listing(
        self, authenticated_client, verified_user, sold_listing
    ):
        """Нельзя купить недоступное объявление."""
        response = authenticated_client.get(
            reverse("transactions:purchase_request_create", kwargs={"listing_pk": sold_listing.pk})
        )

        assert response.status_code == 302

    def test_create_purchase_request_success(
        self, authenticated_client, verified_user, active_listing
    ):
        """Успешное создание запроса."""
        data = {"message": "I want to buy this item"}
        response = authenticated_client.post(
            reverse(
                "transactions:purchase_request_create", kwargs={"listing_pk": active_listing.pk}
            ),
            data,
        )

        assert response.status_code == 302
        assert PurchaseRequest.objects.filter(buyer=verified_user, listing=active_listing).exists()

    def test_duplicate_request_redirects(
        self, authenticated_client, verified_user, active_listing, purchase_request_factory
    ):
        """Дубликат запроса перенаправляет на существующий."""
        existing = purchase_request_factory(active_listing, verified_user)

        response = authenticated_client.get(
            reverse(
                "transactions:purchase_request_create", kwargs={"listing_pk": active_listing.pk}
            )
        )

        assert response.status_code == 302
        assert str(existing.pk) in response.url


@pytest.mark.django_db
class TestPurchaseRequestDetail:
    """Тесты детальной страницы запроса."""

    def test_detail_requires_login(self, client, active_listing, buyer, purchase_request_factory):
        """Детали требуют авторизации."""
        purchase = purchase_request_factory(active_listing, buyer)

        response = client.get(
            reverse("transactions:purchase_request_detail", kwargs={"pk": purchase.pk})
        )
        assert response.status_code == 302

    def test_detail_only_for_participants(
        self, authenticated_client, verified_user, active_listing, buyer, purchase_request_factory
    ):
        """Детали доступны только участникам."""
        purchase = purchase_request_factory(active_listing, buyer)

        # verified_user не участник сделки
        if verified_user not in [purchase.buyer, purchase.seller]:
            response = authenticated_client.get(
                reverse("transactions:purchase_request_detail", kwargs={"pk": purchase.pk})
            )
            assert response.status_code == 302

    def test_can_leave_review_flag(
        self, authenticated_client, buyer, active_listing, purchase_request_factory
    ):
        """Флаг возможности оставить отзыв."""
        client = authenticated_client
        client.force_login(buyer)

        purchase = purchase_request_factory(active_listing, buyer, status="completed")

        response = client.get(
            reverse("transactions:purchase_request_detail", kwargs={"pk": purchase.pk})
        )

        assert response.status_code == 200
        assert response.context["can_leave_review"]


@pytest.mark.django_db
class TestPurchaseRequestActions:
    """Тесты действий с запросами."""

    def test_accept_request(self, client, seller, active_listing, buyer, purchase_request_factory):
        """Принятие запроса: создаёт эскроу и замораживает средства покупателя."""
        from payments.models import Escrow

        _fund_buyer_wallet(buyer)
        client.force_login(seller)
        purchase = purchase_request_factory(active_listing, buyer)

        response = client.post(
            reverse("transactions:purchase_request_accept", kwargs={"pk": purchase.pk})
        )

        assert response.status_code == 302

        purchase.refresh_from_db()
        assert purchase.status == "accepted"
        assert purchase.accepted_at is not None

        active_listing.refresh_from_db()
        assert active_listing.status == "reserved"

        # Эскроу создан и профинансирован
        escrow = Escrow.objects.get(purchase_request=purchase)
        assert escrow.status == "funded"
        assert escrow.amount == active_listing.price

    def test_accept_request_fails_without_buyer_funds(
        self, client, seller, active_listing, buyer, purchase_request_factory
    ):
        """Accept откатывается, если у покупателя недостаточно средств."""
        # buyer без кошелька / с нулевым балансом → fund() упадёт.
        client.force_login(seller)
        purchase = purchase_request_factory(active_listing, buyer)

        response = client.post(
            reverse("transactions:purchase_request_accept", kwargs={"pk": purchase.pk})
        )

        # Контроллер делает redirect с сообщением об ошибке.
        assert response.status_code == 302
        purchase.refresh_from_db()
        # Статус НЕ изменился, листинг не зарезервирован.
        assert purchase.status == "pending"
        active_listing.refresh_from_db()
        assert active_listing.status == "active"

    def test_reject_request(self, client, seller, active_listing, buyer, purchase_request_factory):
        """Отклонение запроса."""
        client.force_login(seller)
        purchase = purchase_request_factory(active_listing, buyer)

        response = client.post(
            reverse("transactions:purchase_request_reject", kwargs={"pk": purchase.pk})
        )

        assert response.status_code == 302

        purchase.refresh_from_db()
        assert purchase.status == "rejected"
        assert purchase.rejected_at is not None

    def test_complete_request_disabled_for_seller(
        self, client, seller, active_listing, buyer, purchase_request_factory
    ):
        """P0-5: продавец БОЛЬШЕ не может сам завершить сделку.

        Раньше seller дёргал purchase_request_complete и забирал эскроу.
        Это закрывало покупателя от защиты эскроу. Теперь — только
        подтверждение покупателя или auto-release по deadline.
        """
        client.force_login(seller)
        purchase = purchase_request_factory(active_listing, buyer, status="accepted")

        response = client.post(
            reverse("transactions:purchase_request_complete", kwargs={"pk": purchase.pk})
        )

        # Redirect с сообщением об ошибке
        assert response.status_code == 302

        purchase.refresh_from_db()
        # Статус НЕ изменился — completion заблокирована для seller-инициативы.
        assert purchase.status == "accepted"

    def test_confirm_received_releases_escrow(
        self, client, seller, active_listing, buyer, purchase_request_factory
    ):
        """Покупатель подтверждает получение → деньги уходят продавцу."""
        from payments.models import Escrow, Wallet

        _fund_buyer_wallet(buyer, amount=Decimal("500.00"))
        # Создаём accepted PR и funded escrow вручную (имитируем accept-flow).
        purchase = purchase_request_factory(active_listing, buyer, status="accepted")
        escrow = Escrow.objects.create(
            purchase_request=purchase,
            buyer=buyer,
            seller=seller,
            amount=active_listing.price,
        )
        escrow.fund()

        client.force_login(buyer)
        response = client.post(
            reverse(
                "transactions:purchase_request_confirm_received",
                kwargs={"pk": purchase.pk},
            )
        )

        assert response.status_code == 302
        purchase.refresh_from_db()
        assert purchase.status == "completed"

        escrow.refresh_from_db()
        assert escrow.status == "released"

        # Деньги перешли продавцу.
        seller_wallet = Wallet.objects.get(user=seller)
        assert seller_wallet.balance == active_listing.price

    def test_cancel_request(
        self, authenticated_client, verified_user, active_listing, purchase_request_factory
    ):
        """Отмена запроса покупателем."""
        purchase = purchase_request_factory(active_listing, verified_user)

        response = authenticated_client.post(
            reverse("transactions:purchase_request_cancel", kwargs={"pk": purchase.pk})
        )

        assert response.status_code == 302

        purchase.refresh_from_db()
        assert purchase.status == "cancelled"
        assert purchase.cancelled_at is not None


@pytest.mark.django_db
class TestReviewCreate:
    """Тесты создания отзыва."""

    def test_review_requires_login(self, client, active_listing, buyer, purchase_request_factory):
        """Создание отзыва требует авторизации."""
        purchase = purchase_request_factory(active_listing, buyer, status="completed")

        response = client.get(
            reverse("transactions:review_create", kwargs={"purchase_request_pk": purchase.pk})
        )
        assert response.status_code == 302

    def test_review_only_for_completed(
        self, authenticated_client, verified_user, active_listing, purchase_request_factory
    ):
        """Отзыв только для завершенных сделок."""
        purchase = purchase_request_factory(active_listing, verified_user, status="pending")

        data = {"rating": 5, "comment": "Great!"}
        response = authenticated_client.post(
            reverse("transactions:review_create", kwargs={"purchase_request_pk": purchase.pk}), data
        )

        # Не должно быть создано
        assert not Review.objects.filter(purchase_request=purchase).exists()

    def test_review_create_success(
        self, authenticated_client, buyer, active_listing, purchase_request_factory
    ):
        """Успешное создание отзыва."""
        authenticated_client.force_login(buyer)
        purchase = purchase_request_factory(active_listing, buyer, status="completed")

        data = {"rating": 5, "comment": "Excellent seller!"}
        response = authenticated_client.post(
            reverse("transactions:review_create", kwargs={"purchase_request_pk": purchase.pk}), data
        )

        assert response.status_code == 302
        assert Review.objects.filter(purchase_request=purchase, reviewer=buyer).exists()

    def test_duplicate_review_prevented(
        self, authenticated_client, buyer, seller, active_listing, purchase_request_factory
    ):
        """Нельзя оставить дубликат отзыва."""
        authenticated_client.force_login(buyer)
        purchase = purchase_request_factory(active_listing, buyer, status="completed")

        # Первый отзыв
        Review.objects.create(
            purchase_request=purchase,
            reviewer=buyer,
            reviewed_user=seller,
            rating=5,
            comment="First",
        )

        # Попытка создать второй
        data = {"rating": 4, "comment": "Second"}
        response = authenticated_client.post(
            reverse("transactions:review_create", kwargs={"purchase_request_pk": purchase.pk}), data
        )

        # Должно быть сообщение о дубликате
        assert Review.objects.filter(purchase_request=purchase, reviewer=buyer).count() == 1
