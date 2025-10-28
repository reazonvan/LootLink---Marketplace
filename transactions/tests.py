"""
Unit тесты для приложения transactions.
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from listings.models import Game, Listing
from .models import PurchaseRequest, Review

User = get_user_model()


class PurchaseRequestModelTest(TestCase):
    """Тесты для модели PurchaseRequest."""
    
    def setUp(self):
        self.seller = User.objects.create_user(
            username='seller',
            email='seller@example.com',
            password='pass123'
        )
        self.buyer = User.objects.create_user(
            username='buyer',
            email='buyer@example.com',
            password='pass123'
        )
        self.game = Game.objects.create(name='Test Game', slug='test-game')
        self.listing = Listing.objects.create(
            seller=self.seller,
            game=self.game,
            title='Test Item',
            description='Test description',
            price=100.00
        )
    
    def test_purchase_request_creation(self):
        """Тест создания запроса на покупку."""
        request = PurchaseRequest.objects.create(
            listing=self.listing,
            buyer=self.buyer,
            seller=self.seller
        )
        
        self.assertEqual(request.status, 'pending')
        self.assertEqual(request.buyer, self.buyer)
        self.assertEqual(request.seller, self.seller)
    
    def test_unique_request_per_buyer_listing(self):
        """Тест уникальности запроса (один покупатель - одно объявление)."""
        PurchaseRequest.objects.create(
            listing=self.listing,
            buyer=self.buyer,
            seller=self.seller
        )
        
        # Попытка создать второй запрос должна вызвать ошибку
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            PurchaseRequest.objects.create(
                listing=self.listing,
                buyer=self.buyer,
                seller=self.seller
            )
    
    def test_accept_purchase_request(self):
        """Тест принятия запроса."""
        request = PurchaseRequest.objects.create(
            listing=self.listing,
            buyer=self.buyer,
            seller=self.seller
        )
        
        request.accept()
        
        self.assertEqual(request.status, 'accepted')
        self.listing.refresh_from_db()
        self.assertEqual(self.listing.status, 'reserved')
    
    def test_complete_purchase_updates_statistics(self):
        """Тест обновления статистики при завершении сделки."""
        request = PurchaseRequest.objects.create(
            listing=self.listing,
            buyer=self.buyer,
            seller=self.seller,
            status='accepted'
        )
        
        # Запоминаем начальные значения
        seller_sales_before = self.seller.profile.total_sales
        buyer_purchases_before = self.buyer.profile.total_purchases
        
        request.complete()
        
        # Обновляем профили
        self.seller.profile.refresh_from_db()
        self.buyer.profile.refresh_from_db()
        
        # Проверяем обновление статистики
        self.assertEqual(self.seller.profile.total_sales, seller_sales_before + 1)
        self.assertEqual(self.buyer.profile.total_purchases, buyer_purchases_before + 1)
        self.assertEqual(request.status, 'completed')
        
        self.listing.refresh_from_db()
        self.assertEqual(self.listing.status, 'sold')


class ReviewModelTest(TestCase):
    """Тесты для модели Review."""
    
    def setUp(self):
        self.seller = User.objects.create_user(
            username='seller',
            email='seller@example.com',
            password='pass123'
        )
        self.buyer = User.objects.create_user(
            username='buyer',
            email='buyer@example.com',
            password='pass123'
        )
        self.game = Game.objects.create(name='Test Game', slug='test-game')
        self.listing = Listing.objects.create(
            seller=self.seller,
            game=self.game,
            title='Test Item',
            description='Test',
            price=100.00
        )
        self.purchase = PurchaseRequest.objects.create(
            listing=self.listing,
            buyer=self.buyer,
            seller=self.seller,
            status='completed'
        )
    
    def test_review_creation(self):
        """Тест создания отзыва."""
        review = Review.objects.create(
            purchase_request=self.purchase,
            reviewer=self.buyer,
            reviewed_user=self.seller,
            rating=5,
            comment='Excellent!'
        )
        
        self.assertEqual(review.rating, 5)
        self.assertEqual(review.reviewer, self.buyer)
    
    def test_rating_updates_profile(self):
        """Тест обновления рейтинга в профиле."""
        Review.objects.create(
            purchase_request=self.purchase,
            reviewer=self.buyer,
            reviewed_user=self.seller,
            rating=5,
            comment='Great!'
        )
        
        self.seller.profile.refresh_from_db()
        self.assertEqual(self.seller.profile.rating, 5.00)
    
    def test_unique_review_per_user_purchase(self):
        """Тест уникальности отзыва (один отзыв на сделку от пользователя)."""
        Review.objects.create(
            purchase_request=self.purchase,
            reviewer=self.buyer,
            reviewed_user=self.seller,
            rating=5
        )
        
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            Review.objects.create(
                purchase_request=self.purchase,
                reviewer=self.buyer,
                reviewed_user=self.seller,
                rating=4
            )

