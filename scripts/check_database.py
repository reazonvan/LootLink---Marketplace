#!/usr/bin/env python
"""
Скрипт для проверки базы данных на наличие тестовых данных.
Анализирует пользователей, объявления и другие данные.

Запуск: python scripts/check_database.py
"""
import os
import sys
import django

# Настройка Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from accounts.models import CustomUser, Profile
from listings.models import Listing, Game
from transactions.models import PurchaseRequest
from payments.models import Wallet, Transaction
from chat.models import Conversation, Message

print("=" * 80)
print("  АНАЛИЗ БАЗЫ ДАННЫХ")
print("=" * 80)
print()

# Паттерны для определения тестовых данных
TEST_PATTERNS = [
    'demo', 'test', 'fake', 'admin@example', 'test@test', 
    'user@example', '@example.com', '@test.com', '@lootlink.com'
]

OWNER_USERNAME = 'reazonvan'

# ==================== АНАЛИЗ ПОЛЬЗОВАТЕЛЕЙ ====================
print("[1] АНАЛИЗ ПОЛЬЗОВАТЕЛЕЙ")
print("-" * 80)

all_users = CustomUser.objects.all()
print(f"Всего пользователей в БД: {all_users.count()}")
print()

# Владелец
owner = CustomUser.objects.filter(username__iexact=OWNER_USERNAME).first()
if owner:
    print(f"[OWNER] Владелец найден: {owner.username} ({owner.email})")
    print(f"        Зарегистрирован: {owner.date_joined.strftime('%Y-%m-%d')}")
    print(f"        Объявлений: {owner.listings.count()}")
    print(f"        Статус: {'Активен' if owner.is_active else 'Деактивирован'}")
else:
    print(f"[!] ВНИМАНИЕ: Владелец '{OWNER_USERNAME}' не найден в БД!")
print()

# Реальные пользователи (не тестовые)
print("[REAL USERS] Реальные пользователи:")
real_users = []
test_users = []

for user in all_users:
    is_test = False
    
    # Проверка на тестовые паттерны
    username_lower = user.username.lower()
    email_lower = user.email.lower()
    
    for pattern in TEST_PATTERNS:
        if pattern in username_lower or pattern in email_lower:
            is_test = True
            break
    
    if is_test:
        test_users.append(user)
    else:
        real_users.append(user)
        print(f"  - {user.username:20} | {user.email:35} | Объявл: {user.listings.count():3} | {user.date_joined.strftime('%Y-%m-%d')}")

print()
print(f"Реальных пользователей: {len(real_users)}")
print()

# Тестовые пользователи
if test_users:
    print("[TEST USERS] Подозрительные/тестовые пользователи:")
    for user in test_users:
        print(f"  [!] {user.username:20} | {user.email:35} | Объявл: {user.listings.count():3}")
    print()
    print(f"Тестовых пользователей: {len(test_users)}")
else:
    print("[OK] Тестовых пользователей не найдено")
print()

# ==================== АНАЛИЗ ОБЪЯВЛЕНИЙ ====================
print("[2] АНАЛИЗ ОБЪЯВЛЕНИЙ")
print("-" * 80)

all_listings = Listing.objects.all()
print(f"Всего объявлений: {all_listings.count()}")
print()

# Объявления от владельца
if owner:
    owner_listings = Listing.objects.filter(seller=owner)
    print(f"Объявлений от владельца ({owner.username}): {owner_listings.count()}")
    if owner_listings.exists():
        for listing in owner_listings[:5]:
            print(f"  - {listing.title[:50]:50} | {listing.price} ₽ | {listing.status}")
        if owner_listings.count() > 5:
            print(f"  ... и еще {owner_listings.count() - 5} объявлений")
    print()

# Объявления от тестовых пользователей
if test_users:
    test_listings_count = Listing.objects.filter(seller__in=test_users).count()
    print(f"[!] Объявлений от тестовых пользователей: {test_listings_count}")
    if test_listings_count > 0:
        for user in test_users:
            user_listings = user.listings.count()
            if user_listings > 0:
                print(f"    {user.username}: {user_listings} объявлений")
    print()

# ==================== АНАЛИЗ ТРАНЗАКЦИЙ ====================
print("[3] АНАЛИЗ ТРАНЗАКЦИЙ И ПОКУПОК")
print("-" * 80)

purchase_requests = PurchaseRequest.objects.all()
print(f"Всего запросов на покупку: {purchase_requests.count()}")

if owner:
    owner_purchases_buyer = PurchaseRequest.objects.filter(buyer=owner).count()
    owner_purchases_seller = PurchaseRequest.objects.filter(seller=owner).count()
    print(f"  - {owner.username} как покупатель: {owner_purchases_buyer}")
    print(f"  - {owner.username} как продавец: {owner_purchases_seller}")
print()

transactions = Transaction.objects.all()
print(f"Всего транзакций: {transactions.count()}")
if owner:
    owner_transactions = Transaction.objects.filter(user=owner).count()
    print(f"  - Транзакций {owner.username}: {owner_transactions}")
print()

# ==================== АНАЛИЗ СООБЩЕНИЙ ====================
print("[4] АНАЛИЗ СООБЩЕНИЙ")
print("-" * 80)

conversations = Conversation.objects.all()
messages = Message.objects.all()
print(f"Всего диалогов: {conversations.count()}")
print(f"Всего сообщений: {messages.count()}")
print()

# ==================== АНАЛИЗ КОШЕЛЬКОВ ====================
print("[5] АНАЛИЗ КОШЕЛЬКОВ")
print("-" * 80)

wallets = Wallet.objects.all()
print(f"Всего кошельков: {wallets.count()}")

if owner:
    owner_wallet = Wallet.objects.filter(user=owner).first()
    if owner_wallet:
        print(f"Кошелек {owner.username}:")
        print(f"  - Баланс: {owner_wallet.balance} ₽")
        print(f"  - Заморожено: {owner_wallet.frozen_balance} ₽")
        print(f"  - Доступно: {owner_wallet.get_available_balance()} ₽")
    else:
        print(f"[i] У {owner.username} нет кошелька")
print()

# Кошельки с балансом
wallets_with_balance = Wallet.objects.filter(balance__gt=0)
if wallets_with_balance.exists():
    print("Кошельки с балансом:")
    for wallet in wallets_with_balance:
        print(f"  - {wallet.user.username:20} | Баланс: {wallet.balance:8} ₽ | Заморожено: {wallet.frozen_balance:8} ₽")
    print()

# ==================== АНАЛИЗ ИГР ====================
print("[6] АНАЛИЗ ИГР")
print("-" * 80)

games = Game.objects.all()
print(f"Всего игр в каталоге: {games.count()}")

active_games = Game.objects.filter(is_active=True)
print(f"Активных игр: {active_games.count()}")
if active_games.exists():
    for game in active_games[:10]:
        listings_count = Listing.objects.filter(game=game).count()
        print(f"  - {game.name:30} | Объявлений: {listings_count:3}")
    if active_games.count() > 10:
        print(f"  ... и еще {active_games.count() - 10} игр")
print()

# ==================== ИТОГИ ====================
print("=" * 80)
print("  ИТОГИ АНАЛИЗА")
print("=" * 80)

print(f"[STATS] Статистика:")
print(f"  Всего пользователей:        {all_users.count()}")
print(f"  - Реальных:                 {len(real_users)}")
print(f"  - Тестовых/подозрительных:  {len(test_users)}")
print(f"  Всего объявлений:           {all_listings.count()}")
if test_users:
    print(f"  - От тестовых пользователей: {Listing.objects.filter(seller__in=test_users).count()}")
print(f"  Всего транзакций:           {transactions.count()}")
print(f"  Всего сообщений:            {messages.count()}")
print()

# Рекомендации
print("[RECOMMENDATIONS] Рекомендации:")
if test_users:
    print(f"  [!] Найдено {len(test_users)} тестовых пользователей - рекомендуется удалить")
    print(f"      Для удаления запустите: python scripts/cleanup_database.py")
else:
    print(f"  [OK] Тестовых пользователей не найдено")

if owner:
    print(f"  [OK] Владелец '{owner.username}' в безопасности")
else:
    print(f"  [!] Владелец '{OWNER_USERNAME}' не найден - ВНИМАНИЕ!")

print()
print("=" * 80)
print("  Анализ завершен")
print("=" * 80)

