"""
Management command для создания дополнительных индексов для оптимизации производительности.
"""
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'Создает дополнительные composite indexes для оптимизации производительности'
    
    def handle(self, *args, **options):
        self.stdout.write('Создание composite indexes...')
        
        with connection.cursor() as cursor:
            # Проверяем и создаем индексы если их нет
            
            # 1. Listing: game + category + status (для фильтрации)
            self.create_index_if_not_exists(
                cursor,
                'idx_listing_game_category_status',
                'listings_listing',
                ['game_id', 'category_id', 'status']
            )
            
            # 2. Listing: game + status + created_at (для списков с сортировкой)
            self.create_index_if_not_exists(
                cursor,
                'idx_listing_game_status_created',
                'listings_listing',
                ['game_id', 'status', 'created_at DESC']
            )
            
            # 3. PurchaseRequest: buyer + status (для списка покупок пользователя)
            self.create_index_if_not_exists(
                cursor,
                'idx_purchase_buyer_status',
                'transactions_purchaserequest',
                ['buyer_id', 'status']
            )
            
            # 4. PurchaseRequest: seller + status (для списка продаж пользователя)
            self.create_index_if_not_exists(
                cursor,
                'idx_purchase_seller_status',
                'transactions_purchaserequest',
                ['seller_id', 'status']
            )
            
            # 5. Message: conversation + created_at (для сортировки сообщений)
            self.create_index_if_not_exists(
                cursor,
                'idx_message_conversation_created',
                'chat_message',
                ['conversation_id', 'created_at']
            )
            
            # 6. Transaction: user + status + created_at (для истории транзакций)
            self.create_index_if_not_exists(
                cursor,
                'idx_transaction_user_status_created',
                'payments_transaction',
                ['user_id', 'status', 'created_at DESC']
            )
            
            # 7. Review: reviewed_user + created_at (для отзывов пользователя)
            self.create_index_if_not_exists(
                cursor,
                'idx_review_reviewed_user_created',
                'transactions_review',
                ['reviewed_user_id', 'created_at DESC']
            )
            
            # 8. Notification: user + is_read + created_at (для уведомлений)
            self.create_index_if_not_exists(
                cursor,
                'idx_notification_user_read_created',
                'core_notification',
                ['user_id', 'is_read', 'created_at DESC']
            )
        
        self.stdout.write(self.style.SUCCESS('✅ Все indexes созданы успешно!'))
    
    def create_index_if_not_exists(self, cursor, index_name, table_name, columns):
        """Создает индекс если его еще нет."""
        # Проверяем существование индекса
        cursor.execute("""
            SELECT 1 
            FROM pg_indexes 
            WHERE indexname = %s
        """, [index_name])
        
        if cursor.fetchone():
            self.stdout.write(f'  ⏭️  Индекс {index_name} уже существует')
            return
        
        # Создаем индекс
        columns_str = ', '.join(columns)
        sql = f'CREATE INDEX CONCURRENTLY {index_name} ON {table_name} ({columns_str})'
        
        try:
            # CONCURRENTLY позволяет создавать индексы без блокировки таблицы
            cursor.execute(sql)
            self.stdout.write(self.style.SUCCESS(f'  ✅ Создан индекс: {index_name}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  ❌ Ошибка создания {index_name}: {e}'))

