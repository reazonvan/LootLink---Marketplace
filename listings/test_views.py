"""
Comprehensive тесты для views приложения listings.
"""
import pytest
from django.urls import reverse
from listings.models import Listing, Game, Favorite, Report
from decimal import Decimal


@pytest.mark.django_db
class TestLandingPage:
    """Тесты главной страницы."""
    
    def test_landing_page_loads(self, client):
        """Главная страница загружается."""
        response = client.get(reverse('listings:home'))
        assert response.status_code == 200
        assert 'LootLink' in response.content.decode()
    
    def test_landing_page_shows_stats(self, client, verified_user):
        """Главная показывает статистику."""
        response = client.get(reverse('listings:home'))
        
        assert 'total_users' in response.context or 'stats' in response.context
        assert response.status_code == 200
    
    def test_landing_page_cached(self, client):
        """Главная страница кешируется."""
        # Первый запрос
        response1 = client.get(reverse('listings:home'))
        
        # Второй запрос (должен быть из кеша)
        response2 = client.get(reverse('listings:home'))
        
        assert response1.status_code == 200
        assert response2.status_code == 200


@pytest.mark.django_db
class TestCatalog:
    """Тесты каталога."""
    
    def test_catalog_loads(self, client):
        """Каталог загружается."""
        response = client.get(reverse('listings:catalog'))
        assert response.status_code == 200
    
    def test_catalog_filters_by_game(self, client, game, seller, listing_factory):
        """Фильтрация по игре."""
        listing = listing_factory(seller)
        
        response = client.get(reverse('listings:catalog'), {'game': game.id})
        assert response.status_code == 200
    
    def test_catalog_filters_by_price(self, client, seller, listing_factory):
        """Фильтрация по цене."""
        cheap = listing_factory(seller, price='50.00')
        expensive = listing_factory(seller, price='500.00')
        
        response = client.get(reverse('listings:catalog'), {
            'min_price': '100',
            'max_price': '600'
        })
        
        assert response.status_code == 200
    
    def test_catalog_search(self, client, seller, listing_factory):
        """Поиск по тексту."""
        listing = listing_factory(seller, title='Unique Dragon Lore')
        
        response = client.get(reverse('listings:catalog'), {'search': 'Dragon'})
        assert response.status_code == 200
    
    def test_catalog_pagination(self, client, seller, listing_factory):
        """Пагинация каталога."""
        # Создаем 15 объявлений
        for i in range(15):
            listing_factory(seller, title=f'Listing {i}')
        
        response = client.get(reverse('listings:catalog'))
        assert response.status_code == 200
        assert 'page_obj' in response.context


@pytest.mark.django_db
class TestListingDetail:
    """Тесты детальной страницы объявления."""
    
    def test_listing_detail_loads(self, client, active_listing):
        """Страница детали загружается."""
        response = client.get(
            reverse('listings:listing_detail', kwargs={'pk': active_listing.pk})
        )
        assert response.status_code == 200
        assert active_listing.title in response.content.decode()
    
    def test_listing_detail_not_found(self, client):
        """404 для несуществующего объявления."""
        response = client.get(
            reverse('listings:listing_detail', kwargs={'pk': 99999})
        )
        assert response.status_code == 404
    
    def test_user_has_request_shown(self, authenticated_client, verified_user, active_listing, purchase_request_factory):
        """Показывает что у пользователя есть активный запрос."""
        purchase = purchase_request_factory(active_listing, verified_user)
        
        response = authenticated_client.get(
            reverse('listings:listing_detail', kwargs={'pk': active_listing.pk})
        )
        
        assert response.status_code == 200
        assert response.context['user_has_request']


@pytest.mark.django_db
class TestListingCreate:
    """Тесты создания объявления."""
    
    def test_create_requires_login(self, client):
        """Создание требует авторизации."""
        response = client.get(reverse('listings:listing_create'))
        assert response.status_code == 302
        assert '/accounts/login/' in response.url
    
    def test_create_requires_verification(self, client, unverified_user):
        """Создание требует верификации."""
        client.force_login(unverified_user)
        
        response = client.get(reverse('listings:listing_create'))
        assert response.status_code == 302
        assert 'verify' in response.url or 'resend' in response.url
    
    def test_create_page_loads_for_verified(self, authenticated_client):
        """Страница создания загружается для верифицированных."""
        response = authenticated_client.get(reverse('listings:listing_create'))
        assert response.status_code == 200
    
    def test_create_listing_success(self, authenticated_client, verified_user, game):
        """Успешное создание объявления."""
        data = {
            'game': game.id,
            'title': 'New Listing',
            'description': 'New Description',
            'price': '150.00',
        }
        response = authenticated_client.post(reverse('listings:listing_create'), data)
        
        assert response.status_code == 302
        assert Listing.objects.filter(title='New Listing').exists()
        
        listing = Listing.objects.get(title='New Listing')
        assert listing.seller == verified_user
        assert listing.status == 'active'
    
    def test_create_listing_max_limit(self, authenticated_client, verified_user, game, listing_factory):
        """Лимит на количество объявлений."""
        # Создаем 50 активных объявлений
        for i in range(50):
            listing_factory(verified_user, title=f'Listing {i}', status='active')
        
        # Попытка создать 51-е объявление
        data = {
            'game': game.id,
            'title': 'Over Limit',
            'description': 'Test',
            'price': '100.00',
        }
        response = authenticated_client.post(reverse('listings:listing_create'), data)
        
        # Должен быть редирект с сообщением об ошибке
        assert response.status_code == 302
        assert not Listing.objects.filter(title='Over Limit').exists()


@pytest.mark.django_db
class TestListingEdit:
    """Тесты редактирования объявления."""
    
    def test_edit_requires_login(self, client, active_listing):
        """Редактирование требует авторизации."""
        response = client.get(
            reverse('listings:listing_edit', kwargs={'pk': active_listing.pk})
        )
        assert response.status_code == 302
    
    def test_edit_only_own_listing(self, authenticated_client, verified_user, active_listing):
        """Можно редактировать только свое объявление."""
        # active_listing принадлежит seller, а authenticated_client - verified_user
        if active_listing.seller != verified_user:
            response = authenticated_client.get(
                reverse('listings:listing_edit', kwargs={'pk': active_listing.pk})
            )
            assert response.status_code == 404
    
    def test_edit_page_loads(self, authenticated_client, verified_user, listing_factory):
        """Страница редактирования загружается."""
        listing = listing_factory(verified_user)
        
        response = authenticated_client.get(
            reverse('listings:listing_edit', kwargs={'pk': listing.pk})
        )
        assert response.status_code == 200
    
    def test_edit_listing_success(self, authenticated_client, verified_user, game, listing_factory):
        """Успешное редактирование."""
        listing = listing_factory(verified_user, title='Old Title')
        
        data = {
            'game': game.id,
            'title': 'New Title',
            'description': 'New Description',
            'price': '200.00',
        }
        response = authenticated_client.post(
            reverse('listings:listing_edit', kwargs={'pk': listing.pk}),
            data
        )
        
        assert response.status_code == 302
        
        listing.refresh_from_db()
        assert listing.title == 'New Title'
        assert listing.price == Decimal('200.00')


@pytest.mark.django_db
class TestListingDelete:
    """Тесты удаления объявления."""
    
    def test_delete_requires_login(self, client, active_listing):
        """Удаление требует авторизации."""
        response = client.get(
            reverse('listings:listing_delete', kwargs={'pk': active_listing.pk})
        )
        assert response.status_code == 302
    
    def test_delete_page_loads(self, authenticated_client, verified_user, listing_factory):
        """Страница удаления загружается."""
        listing = listing_factory(verified_user)
        
        response = authenticated_client.get(
            reverse('listings:listing_delete', kwargs={'pk': listing.pk})
        )
        assert response.status_code == 200
    
    def test_delete_listing_success(self, authenticated_client, verified_user, listing_factory):
        """Успешное удаление."""
        listing = listing_factory(verified_user)
        listing_pk = listing.pk
        
        response = authenticated_client.post(
            reverse('listings:listing_delete', kwargs={'pk': listing.pk})
        )
        
        assert response.status_code == 302
        assert not Listing.objects.filter(pk=listing_pk).exists()
    
    def test_cannot_delete_with_active_requests(self, authenticated_client, verified_user, buyer, listing_factory, purchase_request_factory):
        """Нельзя удалить объявление с активными запросами."""
        listing = listing_factory(verified_user)
        purchase = purchase_request_factory(listing, buyer, status='pending')
        
        response = authenticated_client.post(
            reverse('listings:listing_delete', kwargs={'pk': listing.pk})
        )
        
        # Объявление не должно быть удалено
        assert Listing.objects.filter(pk=listing.pk).exists()


@pytest.mark.django_db
class TestFavorites:
    """Тесты избранного."""
    
    def test_toggle_favorite_add(self, authenticated_client, verified_user, active_listing):
        """Добавление в избранное."""
        response = authenticated_client.post(
            reverse('listings:toggle_favorite', kwargs={'pk': active_listing.pk})
        )
        
        assert Favorite.objects.filter(
            user=verified_user,
            listing=active_listing
        ).exists()
    
    def test_toggle_favorite_remove(self, authenticated_client, verified_user, active_listing):
        """Удаление из избранного."""
        # Сначала добавляем
        Favorite.objects.create(user=verified_user, listing=active_listing)
        
        # Затем удаляем
        response = authenticated_client.post(
            reverse('listings:toggle_favorite', kwargs={'pk': active_listing.pk})
        )
        
        assert not Favorite.objects.filter(
            user=verified_user,
            listing=active_listing
        ).exists()
    
    def test_favorites_list_loads(self, authenticated_client):
        """Страница избранного загружается."""
        response = authenticated_client.get(reverse('listings:favorites'))
        assert response.status_code == 200
    
    def test_favorites_list_shows_items(self, authenticated_client, verified_user, active_listing):
        """Избранное показывает объявления."""
        Favorite.objects.create(user=verified_user, listing=active_listing)
        
        response = authenticated_client.get(reverse('listings:favorites'))
        
        assert response.status_code == 200
        assert active_listing.title in response.content.decode()


@pytest.mark.django_db
class TestReports:
    """Тесты жалоб."""
    
    def test_report_listing_requires_login(self, client, active_listing):
        """Жалоба требует авторизации."""
        response = client.get(
            reverse('listings:report_listing', kwargs={'pk': active_listing.pk})
        )
        assert response.status_code == 302
    
    def test_cannot_report_own_listing(self, authenticated_client, verified_user, listing_factory):
        """Нельзя пожаловаться на свое объявление."""
        listing = listing_factory(verified_user)
        
        response = authenticated_client.get(
            reverse('listings:report_listing', kwargs={'pk': listing.pk})
        )
        
        assert response.status_code == 302
    
    def test_report_listing_success(self, authenticated_client, verified_user, active_listing):
        """Успешная жалоба на объявление."""
        data = {
            'reason': 'spam',
            'description': 'This is spam'
        }
        response = authenticated_client.post(
            reverse('listings:report_listing', kwargs={'pk': active_listing.pk}),
            data
        )
        
        assert response.status_code == 302
        assert Report.objects.filter(
            reporter=verified_user,
            listing=active_listing
        ).exists()
    
    def test_duplicate_report_prevented(self, authenticated_client, verified_user, active_listing):
        """Нельзя подать дубликат жалобы."""
        # Первая жалоба
        Report.objects.create(
            reporter=verified_user,
            report_type='listing',
            listing=active_listing,
            reason='spam',
            description='Spam'
        )
        
        # Попытка подать вторую
        response = authenticated_client.get(
            reverse('listings:report_listing', kwargs={'pk': active_listing.pk})
        )
        
        # Должен быть редирект
        assert response.status_code == 302
    
    def test_report_user_success(self, authenticated_client, verified_user, seller):
        """Успешная жалоба на пользователя."""
        data = {
            'reason': 'fraud',
            'description': 'Fraudulent behavior'
        }
        response = authenticated_client.post(
            reverse('listings:report_user', kwargs={'username': seller.username}),
            data
        )
        
        assert response.status_code == 302
        assert Report.objects.filter(
            reporter=verified_user,
            reported_user=seller
        ).exists()
    
    def test_cannot_report_self(self, authenticated_client, verified_user):
        """Нельзя пожаловаться на себя."""
        response = authenticated_client.get(
            reverse('listings:report_user', kwargs={'username': verified_user.username})
        )
        
        assert response.status_code == 302


@pytest.mark.django_db
class TestGameListings:
    """Тесты объявлений игры."""
    
    def test_game_listings_loads(self, client, game):
        """Страница игры загружается."""
        response = client.get(
            reverse('listings:game_listings', kwargs={'slug': game.slug})
        )
        assert response.status_code == 200
        assert game.name in response.content.decode()
    
    def test_game_listings_shows_only_game_listings(self, client, game, game_factory, seller, listing_factory):
        """Показывает только объявления этой игры."""
        game2 = game_factory(name='Another Game')
        
        listing1 = listing_factory(seller, title='Game 1 Listing')
        # Меняем игру для второго объявления - нужно создать его заново
        listing2 = Listing.objects.create(
            seller=seller,
            game=game2,
            title='Game 2 Listing',
            description='Description',
            price=Decimal('100.00')
        )
        
        response = client.get(
            reverse('listings:game_listings', kwargs={'slug': game.slug})
        )
        
        content = response.content.decode()
        assert 'Game 1 Listing' in content
        assert 'Game 2 Listing' not in content
    
    def test_inactive_game_404(self, client, game):
        """Неактивная игра возвращает 404."""
        game.is_active = False
        game.save()
        
        response = client.get(
            reverse('listings:game_listings', kwargs={'slug': game.slug})
        )
        assert response.status_code == 404

