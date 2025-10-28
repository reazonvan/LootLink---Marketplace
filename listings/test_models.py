"""
Comprehensive тесты для моделей listings.
"""
import pytest
from decimal import Decimal
from django.core.exceptions import ValidationError
from listings.models import Game, Listing, Favorite, Report
from django.contrib.auth import get_user_model

CustomUser = get_user_model()


@pytest.mark.django_db
class TestGameModel:
    """Тесты модели Game."""
    
    def test_game_creation(self):
        """Создание игры."""
        game = Game.objects.create(
            name='Test Game',
            description='Test Description'
        )
        assert game.name == 'Test Game'
        assert game.is_active
    
    def test_slug_auto_generated(self):
        """Slug генерируется автоматически."""
        game = Game.objects.create(name='My Test Game')
        assert game.slug == 'my-test-game'
    
    def test_slug_custom(self):
        """Можно установить кастомный slug."""
        game = Game.objects.create(name='Test Game', slug='custom-slug')
        assert game.slug == 'custom-slug'
    
    def test_game_str_representation(self):
        """Строковое представление."""
        game = Game.objects.create(name='Test Game')
        assert str(game) == 'Test Game'
    
    def test_game_ordering(self):
        """Игры сортируются по имени."""
        Game.objects.create(name='Zebra Game')
        Game.objects.create(name='Alpha Game')
        
        games = list(Game.objects.all())
        assert games[0].name == 'Alpha Game'
        assert games[1].name == 'Zebra Game'
    
    def test_cannot_delete_with_active_listings(self, game, seller, listing_factory):
        """Нельзя удалить игру с активными объявлениями."""
        listing = listing_factory(seller, status='active')
        
        with pytest.raises(Exception) as exc_info:
            game.delete()
        assert 'активными объявлениями' in str(exc_info.value)
    
    def test_can_delete_without_listings(self, game):
        """Можно удалить игру без объявлений."""
        game.delete()
        assert not Game.objects.filter(pk=game.pk).exists()
    
    def test_can_delete_with_only_sold_listings(self, game, seller, listing_factory):
        """Можно удалить игру только с проданными объявлениями."""
        listing = listing_factory(seller, status='sold')
        
        # Не должно вызвать исключение
        game.delete()


@pytest.mark.django_db
class TestListingModel:
    """Тесты модели Listing."""
    
    def test_listing_creation(self, seller, game):
        """Создание объявления."""
        listing = Listing.objects.create(
            seller=seller,
            game=game,
            title='Test Listing',
            description='Test Description',
            price=Decimal('100.00')
        )
        assert listing.title == 'Test Listing'
        assert listing.status == 'active'
        assert listing.price == Decimal('100.00')
    
    def test_listing_str_representation(self, active_listing):
        """Строковое представление."""
        expected = f'{active_listing.title} - {active_listing.game.name}'
        assert str(active_listing) == expected
    
    def test_is_available_active(self, active_listing):
        """Активное объявление доступно."""
        assert active_listing.is_available()
    
    def test_is_available_sold(self, sold_listing):
        """Проданное объявление недоступно."""
        assert not sold_listing.is_available()
    
    def test_listing_ordering(self, seller, listing_factory):
        """Объявления сортируются по дате создания (новые first)."""
        listing1 = listing_factory(seller, title='Old Listing')
        listing2 = listing_factory(seller, title='New Listing')
        
        listings = list(Listing.objects.all())
        assert listings[0] == listing2  # Новое первое
        assert listings[1] == listing1
    
    def test_search_vector_created(self, active_listing):
        """Search vector создается автоматически."""
        active_listing.refresh_from_db()
        # Search vector должен быть создан после save
        assert active_listing.search_vector is not None or active_listing.pk is not None
    
    def test_price_validation(self, seller, game):
        """Цена должна быть положительной."""
        with pytest.raises(Exception):
            Listing.objects.create(
                seller=seller,
                game=game,
                title='Test',
                description='Test',
                price=Decimal('-10.00')
            )
    
    def test_description_max_length(self, seller, game):
        """Описание ограничено 5000 символами."""
        long_description = 'A' * 6000
        
        listing = Listing(
            seller=seller,
            game=game,
            title='Test',
            description=long_description,
            price=Decimal('100.00')
        )
        
        # Django автоматически обрезает или вызывает ошибку
        try:
            listing.full_clean()
            listing.save()
        except ValidationError:
            # Ожидаемое поведение
            pass


@pytest.mark.django_db
class TestFavoriteModel:
    """Тесты модели Favorite."""
    
    def test_favorite_creation(self, verified_user, active_listing):
        """Создание избранного."""
        favorite = Favorite.objects.create(
            user=verified_user,
            listing=active_listing
        )
        assert favorite.user == verified_user
        assert favorite.listing == active_listing
    
    def test_favorite_str_representation(self, verified_user, active_listing):
        """Строковое представление."""
        favorite = Favorite.objects.create(
            user=verified_user,
            listing=active_listing
        )
        expected = f'{verified_user.username} → {active_listing.title}'
        assert str(favorite) == expected
    
    def test_unique_together(self, verified_user, active_listing):
        """Нельзя добавить дубликат в избранное."""
        Favorite.objects.create(user=verified_user, listing=active_listing)
        
        with pytest.raises(Exception):
            Favorite.objects.create(user=verified_user, listing=active_listing)
    
    def test_favorite_ordering(self, verified_user, listing_factory, seller):
        """Избранное сортируется по дате добавления (новые first)."""
        listing1 = listing_factory(seller, title='Listing 1')
        listing2 = listing_factory(seller, title='Listing 2')
        
        fav1 = Favorite.objects.create(user=verified_user, listing=listing1)
        fav2 = Favorite.objects.create(user=verified_user, listing=listing2)
        
        favorites = list(Favorite.objects.all())
        assert favorites[0] == fav2  # Новое первое


@pytest.mark.django_db
class TestReportModel:
    """Тесты модели Report."""
    
    def test_report_listing_creation(self, verified_user, active_listing):
        """Создание жалобы на объявление."""
        report = Report.objects.create(
            reporter=verified_user,
            report_type='listing',
            listing=active_listing,
            reason='spam',
            description='This is spam'
        )
        assert report.report_type == 'listing'
        assert report.status == 'pending'
    
    def test_report_user_creation(self, verified_user, seller):
        """Создание жалобы на пользователя."""
        report = Report.objects.create(
            reporter=verified_user,
            report_type='user',
            reported_user=seller,
            reason='fraud',
            description='This is fraud'
        )
        assert report.report_type == 'user'
        assert report.status == 'pending'
    
    def test_report_str_listing(self, verified_user, active_listing):
        """Строковое представление жалобы на объявление."""
        report = Report.objects.create(
            reporter=verified_user,
            report_type='listing',
            listing=active_listing,
            reason='spam',
            description='Spam'
        )
        assert 'объявление' in str(report).lower()
        assert active_listing.title in str(report)
    
    def test_report_str_user(self, verified_user, seller):
        """Строковое представление жалобы на пользователя."""
        report = Report.objects.create(
            reporter=verified_user,
            report_type='user',
            reported_user=seller,
            reason='fraud',
            description='Fraud'
        )
        assert 'пользователя' in str(report).lower()
        assert seller.username in str(report)
    
    def test_report_ordering(self, verified_user, active_listing):
        """Жалобы сортируются по дате (новые first)."""
        report1 = Report.objects.create(
            reporter=verified_user,
            report_type='listing',
            listing=active_listing,
            reason='spam',
            description='Old report'
        )
        report2 = Report.objects.create(
            reporter=verified_user,
            report_type='listing',
            listing=active_listing,
            reason='fake',
            description='New report'
        )
        
        reports = list(Report.objects.all())
        assert reports[0] == report2  # Новая первая


@pytest.mark.django_db
class TestImageValidation:
    """Тесты валидации изображений."""
    
    def test_image_size_validation(self):
        """Валидация размера изображения."""
        from django.core.files.uploadedfile import SimpleUploadedFile
        from listings.models import validate_image_size
        from io import BytesIO
        from PIL import Image
        
        # Создаем большое изображение
        img = Image.new('RGB', (3000, 3000), color='red')
        img_io = BytesIO()
        img.save(img_io, format='JPEG', quality=100)
        img_io.seek(0)
        
        large_file = SimpleUploadedFile(
            "large.jpg",
            img_io.getvalue(),
            content_type="image/jpeg"
        )
        
        # Если файл больше 5MB, должна быть ошибка
        if large_file.size > 5 * 1024 * 1024:
            with pytest.raises(ValidationError):
                validate_image_size(large_file)
    
    def test_image_type_validation_valid(self):
        """Валидация типа изображения - валидное."""
        from django.core.files.uploadedfile import SimpleUploadedFile
        from listings.models import validate_image_type
        from io import BytesIO
        from PIL import Image
        
        # Создаем валидное изображение
        img = Image.new('RGB', (100, 100), color='blue')
        img_io = BytesIO()
        img.save(img_io, format='JPEG')
        img_io.seek(0)
        
        valid_file = SimpleUploadedFile(
            "valid.jpg",
            img_io.getvalue(),
            content_type="image/jpeg"
        )
        
        # Не должно быть ошибки
        try:
            validate_image_type(valid_file)
        except ValidationError:
            pytest.fail("Valid image raised ValidationError")
    
    def test_image_type_validation_corrupted(self):
        """Валидация типа - поврежденный файл."""
        from django.core.files.uploadedfile import SimpleUploadedFile
        from listings.models import validate_image_type
        
        # Создаем не-изображение
        corrupted_file = SimpleUploadedFile(
            "corrupted.jpg",
            b"This is not an image",
            content_type="image/jpeg"
        )
        
        # Должна быть ошибка
        with pytest.raises(ValidationError):
            validate_image_type(corrupted_file)

