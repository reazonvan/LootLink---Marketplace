"""
Тесты для приложения listings.
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from listings.models import Listing, Game, Favorite
from decimal import Decimal

CustomUser = get_user_model()


class GameModelTest(TestCase):
    """Тесты модели Game."""
    
    def setUp(self):
        self.game = Game.objects.create(
            name='Test Game',
            description='Test Description'
        )
    
    def test_game_slug_auto_generated(self):
        """Slug генерируется автоматически."""
        self.assertIsNotNone(self.game.slug)
        self.assertEqual(self.game.slug, 'test-game')
    
    def test_game_cannot_be_deleted_with_active_listings(self):
        """Игру с активными объявлениями нельзя удалить."""
        user = CustomUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Создаем активное объявление
        Listing.objects.create(
            seller=user,
            game=self.game,
            title='Test Listing',
            description='Test Description',
            price=Decimal('100.00'),
            status='active'
        )
        
        # Пытаемся удалить игру
        with self.assertRaises(Exception):
            self.game.delete()


class ListingModelTest(TestCase):
    """Тесты модели Listing."""
    
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.game = Game.objects.create(
            name='Test Game',
            description='Test Description'
        )
        self.listing = Listing.objects.create(
            seller=self.user,
            game=self.game,
            title='Test Listing',
            description='Test Description',
            price=Decimal('100.00')
        )
    
    def test_listing_created(self):
        """Объявление создается корректно."""
        self.assertIsNotNone(self.listing)
        self.assertEqual(self.listing.title, 'Test Listing')
        self.assertEqual(self.listing.price, Decimal('100.00'))
        self.assertEqual(self.listing.status, 'active')
    
    def test_is_available(self):
        """Метод is_available работает."""
        self.assertTrue(self.listing.is_available())
        
        # Меняем статус
        self.listing.status = 'sold'
        self.listing.save()
        self.assertFalse(self.listing.is_available())


class ListingViewsTest(TestCase):
    """Тесты views для listings."""
    
    def setUp(self):
        self.client = Client()
        self.user = CustomUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        # Верифицируем пользователя
        self.user.profile.is_verified = True
        self.user.profile.save()
        
        self.game = Game.objects.create(
            name='Test Game',
            description='Test Description'
        )
    
    def test_catalog_page_loads(self):
        """Страница каталога загружается."""
        response = self.client.get(reverse('listings:catalog'))
        self.assertEqual(response.status_code, 200)
    
    def test_landing_page_loads(self):
        """Главная страница загружается."""
        response = self.client.get(reverse('listings:home'))
        self.assertEqual(response.status_code, 200)
    
    def test_create_listing_requires_verification(self):
        """Создание объявления требует верификации."""
        # Создаем неверифицированного пользователя
        unverified_user = CustomUser.objects.create_user(
            username='unverified',
            email='unverified@example.com',
            password='testpass123'
        )
        unverified_user.profile.is_verified = False
        unverified_user.profile.save()
        
        # Логинимся
        self.client.login(username='unverified', password='testpass123')
        
        # Пытаемся создать объявление
        response = self.client.get(reverse('listings:listing_create'))
        
        # Должен быть редирект на страницу верификации
        self.assertEqual(response.status_code, 302)
    
    def test_create_listing_success(self):
        """Успешное создание объявления."""
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.post(reverse('listings:listing_create'), {
            'game': self.game.id,
            'title': 'New Listing',
            'description': 'New Description',
            'price': '150.00',
        })
        
        # Проверяем что объявление создано
        self.assertTrue(Listing.objects.filter(title='New Listing').exists())
    
    def test_listing_detail_page(self):
        """Страница деталей объявления."""
        listing = Listing.objects.create(
            seller=self.user,
            game=self.game,
            title='Test Listing',
            description='Test Description',
            price=Decimal('100.00')
        )
        
        response = self.client.get(
            reverse('listings:listing_detail', kwargs={'pk': listing.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Listing')


class FavoriteTest(TestCase):
    """Тесты избранного."""
    
    def setUp(self):
        self.client = Client()
        self.user = CustomUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.game = Game.objects.create(
            name='Test Game',
            description='Test Description'
        )
        self.listing = Listing.objects.create(
            seller=self.user,
            game=self.game,
            title='Test Listing',
            description='Test Description',
            price=Decimal('100.00')
        )
    
    def test_add_to_favorites(self):
        """Добавление в избранное."""
        favorite = Favorite.objects.create(
            user=self.user,
            listing=self.listing
        )
        self.assertIsNotNone(favorite)
        self.assertEqual(self.listing.favorited_by.count(), 1)
    
    def test_duplicate_favorite_prevented(self):
        """Нельзя добавить дубликат в избранное."""
        Favorite.objects.create(user=self.user, listing=self.listing)
        
        # Пытаемся добавить еще раз
        with self.assertRaises(Exception):
            Favorite.objects.create(user=self.user, listing=self.listing)
