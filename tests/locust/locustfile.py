"""
Locust-сценарии для нагрузочного тестирования LootLink.

Запуск:
    pip install locust
    locust -f tests/locust/locustfile.py --host=http://localhost:8000

Web UI:
    http://localhost:8089
    Установить: 100 users, 10 spawn rate, 5 минут.

Headless для CI:
    locust -f tests/locust/locustfile.py --host=https://lootlink.ru \\
        --users 100 --spawn-rate 10 --run-time 5m --headless \\
        --csv=results/locust --html=results/locust.html

Полученные метрики (RPS, p50/p95/p99, throughput) идут в раздел 2.4
дипломного отчёта.
"""
import random

from locust import HttpUser, between, task


class AnonBrowsingUser(HttpUser):
    """
    Анонимный пользователь — основной трафик.
    Просмотр главной, каталога, листингов, поиск.
    """
    wait_time = between(1, 3)

    @task(5)
    def view_landing(self):
        """Главная страница (наибольший вес — 50% запросов)."""
        self.client.get('/', name='/')

    @task(3)
    def view_games_catalog(self):
        """Каталог игр."""
        self.client.get('/games/', name='/games/')

    @task(2)
    def view_listings(self):
        """Список объявлений (с пагинацией)."""
        page = random.randint(1, 5)
        self.client.get(f'/listings/?page={page}', name='/listings/?page=[N]')

    @task(2)
    def search_listings(self):
        """FTS-поиск (показывает русскую морфологию)."""
        queries = ['нож', 'скин', 'аккаунт', 'cs2', 'dota']
        q = random.choice(queries)
        self.client.get(f'/search/?q={q}', name='/search/?q=[Q]')

    @task(1)
    def view_listing_detail(self):
        """Детальная карточка (если ID существует — иначе 404)."""
        listing_id = random.randint(1, 100)
        with self.client.get(
            f'/listing/{listing_id}/',
            name='/listing/[id]/',
            catch_response=True,
        ) as response:
            # 404 не считаем за неудачу — листинг может не существовать.
            if response.status_code == 404:
                response.success()


class AuthenticatedUser(HttpUser):
    """
    Залогиненный пользователь.
    Меньший трафик, более тяжёлые сценарии (профиль, сделки, чат).

    Для запуска нужен fixture-логин — см. on_start.
    """
    wait_time = between(2, 5)
    weight = 1  # реже чем анонимы

    def on_start(self):
        """
        Логинимся при старте. Использует тестовую учётку.
        В продакшене эту user'у нужно зарегистрировать заранее
        и указать креды через env переменные:
            LOCUST_USER, LOCUST_PASSWORD
        """
        import os
        username = os.environ.get('LOCUST_USER', 'demo_buyer')
        password = os.environ.get('LOCUST_PASSWORD', 'demo_pass')

        # Получаем CSRF
        response = self.client.get('/login/')
        csrf = response.cookies.get('csrftoken', '')

        # Логинимся
        self.client.post(
            '/login/',
            data={
                'username': username,
                'password': password,
                'csrfmiddlewaretoken': csrf,
            },
            headers={'Referer': f'{self.host}/login/'},
            name='/login/ [setup]',
        )

    @task(3)
    def view_profile(self):
        """Свой профиль."""
        self.client.get('/profile/', name='/profile/')

    @task(2)
    def view_my_listings(self):
        """Мои объявления."""
        self.client.get('/my-listings/', name='/my-listings/')

    @task(2)
    def view_wallet(self):
        """Кошелёк (баланс, транзакции)."""
        self.client.get('/payments/wallet/', name='/payments/wallet/')

    @task(1)
    def view_conversations(self):
        """Список диалогов."""
        self.client.get('/conversations/', name='/conversations/')

    @task(1)
    def view_purchase_requests(self):
        """История сделок."""
        self.client.get('/transactions/', name='/transactions/')


class APIUser(HttpUser):
    """
    REST API consumer (мобильное приложение, интеграции).
    Меньший вес, чисто JSON-запросы.
    """
    wait_time = between(1, 2)
    weight = 1

    @task(3)
    def api_listings(self):
        """GET /api/listings/."""
        self.client.get('/api/listings/', name='/api/listings/')

    @task(2)
    def api_games(self):
        """GET /api/games/."""
        self.client.get('/api/games/', name='/api/games/')

    @task(1)
    def api_listing_detail(self):
        """GET /api/listings/[id]/."""
        listing_id = random.randint(1, 100)
        with self.client.get(
            f'/api/listings/{listing_id}/',
            name='/api/listings/[id]/',
            catch_response=True,
        ) as response:
            if response.status_code == 404:
                response.success()
