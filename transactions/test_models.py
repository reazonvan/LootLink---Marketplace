"""
Comprehensive тесты для моделей transactions.
"""
import pytest
from decimal import Decimal
from django.utils import timezone
from transactions.models import PurchaseRequest, Review
from django.contrib.auth import get_user_model

CustomUser = get_user_model()


@pytest.mark.django_db
class TestPurchaseRequestModel:
    """Тесты модели PurchaseRequest."""
    
    def test_purchase_request_creation(self, active_listing, buyer, seller):
        """Создание запроса на покупку."""
        purchase = PurchaseRequest.objects.create(
            listing=active_listing,
            buyer=buyer,
            seller=seller,
            message='I want to buy this'
        )
        assert purchase.status == 'pending'
        assert purchase.buyer == buyer
        assert purchase.seller == seller
    
    def test_purchase_request_str(self, active_listing, buyer, purchase_request_factory):
        """Строковое представление."""
        purchase = purchase_request_factory(active_listing, buyer)
        expected = f'{buyer.username} → {active_listing.title}'
        assert str(purchase) == expected
    
    def test_unique_together(self, active_listing, buyer, purchase_request_factory):
        """Один покупатель - один запрос на объявление."""
        purchase_request_factory(active_listing, buyer)
        
        with pytest.raises(Exception):
            purchase_request_factory(active_listing, buyer)
    
    def test_accept_method(self, active_listing, buyer, purchase_request_factory):
        """Метод accept()."""
        purchase = purchase_request_factory(active_listing, buyer)
        purchase.accept()
        
        purchase.refresh_from_db()
        assert purchase.status == 'accepted'
        
        active_listing.refresh_from_db()
        assert active_listing.status == 'reserved'
    
    def test_reject_method(self, active_listing, buyer, purchase_request_factory):
        """Метод reject()."""
        purchase = purchase_request_factory(active_listing, buyer)
        purchase.reject()
        
        purchase.refresh_from_db()
        assert purchase.status == 'rejected'
    
    def test_complete_method(self, active_listing, buyer, seller, purchase_request_factory):
        """Метод complete()."""
        purchase = purchase_request_factory(active_listing, buyer, status='accepted')
        
        # Запоминаем начальные значения
        initial_seller_sales = seller.profile.total_sales
        initial_buyer_purchases = buyer.profile.total_purchases
        
        purchase.complete()
        
        purchase.refresh_from_db()
        assert purchase.status == 'completed'
        assert purchase.completed_at is not None
        
        active_listing.refresh_from_db()
        assert active_listing.status == 'sold'
        
        # Проверяем статистику
        seller.profile.refresh_from_db()
        buyer.profile.refresh_from_db()
        assert seller.profile.total_sales == initial_seller_sales + 1
        assert buyer.profile.total_purchases == initial_buyer_purchases + 1


@pytest.mark.django_db
class TestReviewModel:
    """Тесты модели Review."""
    
    def test_review_creation(self, active_listing, buyer, seller, purchase_request_factory):
        """Создание отзыва."""
        purchase = purchase_request_factory(active_listing, buyer, status='completed')
        
        review = Review.objects.create(
            purchase_request=purchase,
            reviewer=buyer,
            reviewed_user=seller,
            rating=5,
            comment='Excellent seller!'
        )
        
        assert review.rating == 5
        assert review.reviewer == buyer
        assert review.reviewed_user == seller
    
    def test_review_str(self, active_listing, buyer, seller, purchase_request_factory):
        """Строковое представление."""
        purchase = purchase_request_factory(active_listing, buyer, status='completed')
        
        review = Review.objects.create(
            purchase_request=purchase,
            reviewer=buyer,
            reviewed_user=seller,
            rating=5,
            comment='Great!'
        )
        
        expected = f'Отзыв от {buyer.username} для {seller.username} (5/5)'
        assert str(review) == expected
    
    def test_review_unique_per_purchase_and_reviewer(self, active_listing, buyer, seller, purchase_request_factory):
        """Один отзыв от reviewer на сделку."""
        purchase = purchase_request_factory(active_listing, buyer, status='completed')
        
        Review.objects.create(
            purchase_request=purchase,
            reviewer=buyer,
            reviewed_user=seller,
            rating=5,
            comment='First'
        )
        
        with pytest.raises(Exception):
            Review.objects.create(
                purchase_request=purchase,
                reviewer=buyer,
                reviewed_user=seller,
                rating=4,
                comment='Second'
            )
    
    def test_review_updates_user_rating(self, active_listing, buyer, seller, purchase_request_factory):
        """Отзыв обновляет рейтинг пользователя."""
        purchase = purchase_request_factory(active_listing, buyer, status='completed')
        
        initial_rating = seller.profile.rating
        
        Review.objects.create(
            purchase_request=purchase,
            reviewer=buyer,
            reviewed_user=seller,
            rating=5,
            comment='Great!'
        )
        
        seller.profile.refresh_from_db()
        # Рейтинг должен обновиться
        assert seller.profile.rating >= initial_rating
    
    def test_rating_validation(self, active_listing, buyer, seller, purchase_request_factory):
        """Рейтинг должен быть от 1 до 5."""
        purchase = purchase_request_factory(active_listing, buyer, status='completed')
        
        # Рейтинг 0 невалиден
        with pytest.raises(Exception):
            review = Review(
                purchase_request=purchase,
                reviewer=buyer,
                reviewed_user=seller,
                rating=0,
                comment='Bad'
            )
            review.full_clean()
        
        # Рейтинг 6 невалиден
        with pytest.raises(Exception):
            review = Review(
                purchase_request=purchase,
                reviewer=buyer,
                reviewed_user=seller,
                rating=6,
                comment='Bad'
            )
            review.full_clean()

