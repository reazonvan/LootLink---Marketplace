"""
Comprehensive тесты для views приложения transactions.
"""
import pytest
from django.urls import reverse
from transactions.models import PurchaseRequest, Review
from decimal import Decimal


@pytest.mark.django_db
class TestPurchaseRequestCreate:
    """Тесты создания запроса на покупку."""
    
    def test_create_requires_login(self, client, active_listing):
        """Создание требует авторизации."""
        response = client.get(
            reverse('transactions:purchase_request_create', kwargs={'listing_pk': active_listing.pk})
        )
        assert response.status_code == 302
    
    def test_cannot_buy_own_listing(self, authenticated_client, verified_user, listing_factory):
        """Нельзя купить свое объявление."""
        listing = listing_factory(verified_user)
        
        response = authenticated_client.get(
            reverse('transactions:purchase_request_create', kwargs={'listing_pk': listing.pk})
        )
        
        assert response.status_code == 302
    
    def test_cannot_buy_unavailable_listing(self, authenticated_client, verified_user, sold_listing):
        """Нельзя купить недоступное объявление."""
        response = authenticated_client.get(
            reverse('transactions:purchase_request_create', kwargs={'listing_pk': sold_listing.pk})
        )
        
        assert response.status_code == 302
    
    def test_create_purchase_request_success(self, authenticated_client, verified_user, active_listing):
        """Успешное создание запроса."""
        data = {
            'message': 'I want to buy this item'
        }
        response = authenticated_client.post(
            reverse('transactions:purchase_request_create', kwargs={'listing_pk': active_listing.pk}),
            data
        )
        
        assert response.status_code == 302
        assert PurchaseRequest.objects.filter(
            buyer=verified_user,
            listing=active_listing
        ).exists()
    
    def test_duplicate_request_redirects(self, authenticated_client, verified_user, active_listing, purchase_request_factory):
        """Дубликат запроса перенаправляет на существующий."""
        existing = purchase_request_factory(active_listing, verified_user)
        
        response = authenticated_client.get(
            reverse('transactions:purchase_request_create', kwargs={'listing_pk': active_listing.pk})
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
            reverse('transactions:purchase_request_detail', kwargs={'pk': purchase.pk})
        )
        assert response.status_code == 302
    
    def test_detail_only_for_participants(self, authenticated_client, verified_user, active_listing, buyer, purchase_request_factory):
        """Детали доступны только участникам."""
        purchase = purchase_request_factory(active_listing, buyer)
        
        # verified_user не участник сделки
        if verified_user not in [purchase.buyer, purchase.seller]:
            response = authenticated_client.get(
                reverse('transactions:purchase_request_detail', kwargs={'pk': purchase.pk})
            )
            assert response.status_code == 302
    
    def test_can_leave_review_flag(self, authenticated_client, buyer, active_listing, purchase_request_factory):
        """Флаг возможности оставить отзыв."""
        client = authenticated_client
        client.force_login(buyer)
        
        purchase = purchase_request_factory(active_listing, buyer, status='completed')
        
        response = client.get(
            reverse('transactions:purchase_request_detail', kwargs={'pk': purchase.pk})
        )
        
        assert response.status_code == 200
        assert response.context['can_leave_review']


@pytest.mark.django_db
class TestPurchaseRequestActions:
    """Тесты действий с запросами."""
    
    def test_accept_request(self, client, seller, active_listing, buyer, purchase_request_factory):
        """Принятие запроса."""
        client.force_login(seller)
        purchase = purchase_request_factory(active_listing, buyer)
        
        response = client.post(
            reverse('transactions:purchase_request_accept', kwargs={'pk': purchase.pk})
        )
        
        assert response.status_code == 302
        
        purchase.refresh_from_db()
        assert purchase.status == 'accepted'
        
        active_listing.refresh_from_db()
        assert active_listing.status == 'reserved'
    
    def test_reject_request(self, client, seller, active_listing, buyer, purchase_request_factory):
        """Отклонение запроса."""
        client.force_login(seller)
        purchase = purchase_request_factory(active_listing, buyer)
        
        response = client.post(
            reverse('transactions:purchase_request_reject', kwargs={'pk': purchase.pk})
        )
        
        assert response.status_code == 302
        
        purchase.refresh_from_db()
        assert purchase.status == 'rejected'
    
    def test_complete_request(self, client, seller, active_listing, buyer, purchase_request_factory):
        """Завершение сделки."""
        client.force_login(seller)
        purchase = purchase_request_factory(active_listing, buyer, status='accepted')
        
        initial_sales = seller.profile.total_sales
        initial_purchases = buyer.profile.total_purchases
        
        response = client.post(
            reverse('transactions:purchase_request_complete', kwargs={'pk': purchase.pk})
        )
        
        assert response.status_code == 302
        
        purchase.refresh_from_db()
        assert purchase.status == 'completed'
        
        seller.profile.refresh_from_db()
        buyer.profile.refresh_from_db()
        assert seller.profile.total_sales == initial_sales + 1
        assert buyer.profile.total_purchases == initial_purchases + 1
    
    def test_cancel_request(self, authenticated_client, verified_user, active_listing, purchase_request_factory):
        """Отмена запроса покупателем."""
        purchase = purchase_request_factory(active_listing, verified_user)
        
        response = authenticated_client.post(
            reverse('transactions:purchase_request_cancel', kwargs={'pk': purchase.pk})
        )
        
        assert response.status_code == 302
        
        purchase.refresh_from_db()
        assert purchase.status == 'cancelled'


@pytest.mark.django_db
class TestReviewCreate:
    """Тесты создания отзыва."""
    
    def test_review_requires_login(self, client, active_listing, buyer, purchase_request_factory):
        """Создание отзыва требует авторизации."""
        purchase = purchase_request_factory(active_listing, buyer, status='completed')
        
        response = client.get(
            reverse('transactions:review_create', kwargs={'purchase_request_pk': purchase.pk})
        )
        assert response.status_code == 302
    
    def test_review_only_for_completed(self, authenticated_client, verified_user, active_listing, purchase_request_factory):
        """Отзыв только для завершенных сделок."""
        purchase = purchase_request_factory(active_listing, verified_user, status='pending')
        
        data = {
            'rating': 5,
            'comment': 'Great!'
        }
        response = authenticated_client.post(
            reverse('transactions:review_create', kwargs={'purchase_request_pk': purchase.pk}),
            data
        )
        
        # Не должно быть создано
        assert not Review.objects.filter(purchase_request=purchase).exists()
    
    def test_review_create_success(self, authenticated_client, buyer, active_listing, purchase_request_factory):
        """Успешное создание отзыва."""
        authenticated_client.force_login(buyer)
        purchase = purchase_request_factory(active_listing, buyer, status='completed')
        
        data = {
            'rating': 5,
            'comment': 'Excellent seller!'
        }
        response = authenticated_client.post(
            reverse('transactions:review_create', kwargs={'purchase_request_pk': purchase.pk}),
            data
        )
        
        assert response.status_code == 302
        assert Review.objects.filter(
            purchase_request=purchase,
            reviewer=buyer
        ).exists()
    
    def test_duplicate_review_prevented(self, authenticated_client, buyer, seller, active_listing, purchase_request_factory):
        """Нельзя оставить дубликат отзыва."""
        authenticated_client.force_login(buyer)
        purchase = purchase_request_factory(active_listing, buyer, status='completed')
        
        # Первый отзыв
        Review.objects.create(
            purchase_request=purchase,
            reviewer=buyer,
            reviewed_user=seller,
            rating=5,
            comment='First'
        )
        
        # Попытка создать второй
        data = {
            'rating': 4,
            'comment': 'Second'
        }
        response = authenticated_client.post(
            reverse('transactions:review_create', kwargs={'purchase_request_pk': purchase.pk}),
            data
        )
        
        # Должно быть сообщение о дубликате
        assert Review.objects.filter(purchase_request=purchase, reviewer=buyer).count() == 1

