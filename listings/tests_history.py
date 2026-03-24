"""
Тесты для истории просмотров.
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from listings.models import Listing, Game
from listings.models_history import ViewHistory

User = get_user_model()


class ViewHistoryTests(TestCase):
    """Тесты для истории просмотров."""

    def setUp(self):
        """Настройка тестов."""
        # Создаем продавца
        self.seller = User.objects.create_user(
            username='seller',
            email='seller@example.com',
            password='testpass123'
        )
        # Создаем покупателя (просматривающего)
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.game = Game.objects.create(
            name='Test Game',
            slug='test-game'
        )
        self.listing = Listing.objects.create(
            title='Test Listing',
            description='Test description',
            price=100,
            game=self.game,
            seller=self.seller  # Продавец - другой пользователь
        )

    def test_record_view(self):
        """Тест записи просмотра."""
        ViewHistory.record_view(self.user, self.listing)

        # Проверяем что запись создана
        self.assertTrue(
            ViewHistory.objects.filter(
                user=self.user,
                listing=self.listing
            ).exists()
        )

    def test_record_view_updates_timestamp(self):
        """Тест обновления timestamp при повторном просмотре."""
        # Первый просмотр
        ViewHistory.record_view(self.user, self.listing)
        first_view = ViewHistory.objects.get(user=self.user, listing=self.listing)
        first_timestamp = first_view.viewed_at

        # Второй просмотр
        ViewHistory.record_view(self.user, self.listing)
        second_view = ViewHistory.objects.get(user=self.user, listing=self.listing)
        second_timestamp = second_view.viewed_at

        # Timestamp должен обновиться
        self.assertGreater(second_timestamp, first_timestamp)

        # Должна быть только одна запись
        self.assertEqual(
            ViewHistory.objects.filter(user=self.user, listing=self.listing).count(),
            1
        )

    def test_view_limit(self):
        """Тест лимита записей (50)."""
        # Создаем 60 объявлений от продавца
        for i in range(60):
            listing = Listing.objects.create(
                title=f'Listing {i}',
                description='Test',
                price=100,
                game=self.game,
                seller=self.seller  # Продавец - другой пользователь
            )
            ViewHistory.record_view(self.user, listing)

        # Должно быть только 50 записей
        self.assertEqual(
            ViewHistory.objects.filter(user=self.user).count(),
            50
        )
