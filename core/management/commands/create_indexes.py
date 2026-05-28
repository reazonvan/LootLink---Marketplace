"""
Management command для создания дополнительных индексов для оптимизации производительности.
"""

from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Создает дополнительные composite indexes для оптимизации производительности"

    def handle(self, *args, **options):
        self.stdout.write("Создание composite indexes...")

        with connection.cursor() as cursor:
            # Проверяем и создаем индексы если их нет

            # 1. Listing: game + category + status (для фильтрации)
            self.create_index_if_not_exists(
                cursor,
                "idx_listing_game_category_status",
                "listings_listing",
                ["game_id", "category_id", "status"],
            )

            # 2. Listing: game + status + created_at (для списков с сортировкой)
            self.create_index_if_not_exists(
                cursor,
                "idx_listing_game_status_created",
                "listings_listing",
                ["game_id", "status", "created_at DESC"],
            )

            # 3. PurchaseRequest: buyer + status (для списка покупок пользователя)
            self.create_index_if_not_exists(
                cursor,
                "idx_purchase_buyer_status",
                "transactions_purchaserequest",
                ["buyer_id", "status"],
            )

            # 4. PurchaseRequest: seller + status (для списка продаж пользователя)
            self.create_index_if_not_exists(
                cursor,
                "idx_purchase_seller_status",
                "transactions_purchaserequest",
                ["seller_id", "status"],
            )

            # 5. Message: conversation + created_at (для сортировки сообщений)
            self.create_index_if_not_exists(
                cursor,
                "idx_message_conversation_created",
                "chat_message",
                ["conversation_id", "created_at"],
            )

            # 6. Transaction: user + status + created_at (для истории транзакций)
            self.create_index_if_not_exists(
                cursor,
                "idx_transaction_user_status_created",
                "payments_transaction",
                ["user_id", "status", "created_at DESC"],
            )

            # 7. Review: reviewed_user + created_at (для отзывов пользователя)
            self.create_index_if_not_exists(
                cursor,
                "idx_review_reviewed_user_created",
                "transactions_review",
                ["reviewed_user_id", "created_at DESC"],
            )

            # 8. Notification: user + is_read + created_at (для уведомлений)
            self.create_index_if_not_exists(
                cursor,
                "idx_notification_user_read_created",
                "core_notification",
                ["user_id", "is_read", "created_at DESC"],
            )

        self.stdout.write(self.style.SUCCESS("Все indexes созданы успешно!"))

    # A8: whitelist допустимых символов для имен индексов/таблиц/колонок.
    # SQL identifier нельзя параметризовать через %s, поэтому валидируем
    # явно: только [a-zA-Z0-9_], начинается с буквы. Любые другие символы
    # → ValueError. Это закрывает паттерн SQL injection даже для будущих
    # изменений, когда значения могут стать динамическими.
    _SAFE_IDENT_RE = __import__("re").compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")

    @classmethod
    def _validate_identifier(cls, value: str, kind: str) -> str:
        """Бросает ValueError если идентификатор не whitelist-safe."""
        if not isinstance(value, str) or not cls._SAFE_IDENT_RE.match(value):
            raise ValueError(f"Небезопасное {kind}: {value!r}. Допустимы только [a-zA-Z0-9_].")
        return value

    def create_index_if_not_exists(self, cursor, index_name, table_name, columns):
        """Создает индекс если его еще нет (с whitelist-валидацией identifier'ов)."""
        # A8: валидация идентификаторов перед f-string подстановкой
        index_name = self._validate_identifier(index_name, "имя индекса")
        # Имя таблицы может быть `app_table` — это OK.
        table_name = self._validate_identifier(table_name, "имя таблицы")
        # Колонки могут иметь модификатор " DESC" — обрабатываем отдельно.
        safe_cols = []
        for col in columns:
            parts = col.split()
            self._validate_identifier(parts[0], "имя колонки")
            if len(parts) > 1 and parts[1].upper() not in ("ASC", "DESC"):
                raise ValueError(f"Недопустимый модификатор сортировки: {col!r}")
            safe_cols.append(col)

        cursor.execute(
            """
            SELECT 1
            FROM pg_indexes
            WHERE indexname = %s
            """,
            [index_name],
        )

        if cursor.fetchone():
            self.stdout.write(f"  Индекс {index_name} уже существует")
            return

        columns_str = ", ".join(safe_cols)
        sql = f"CREATE INDEX CONCURRENTLY {index_name} ON {table_name} ({columns_str})"

        try:
            cursor.execute(sql)
            self.stdout.write(self.style.SUCCESS(f"  Создан индекс: {index_name}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  Ошибка создания {index_name}: {e}"))
