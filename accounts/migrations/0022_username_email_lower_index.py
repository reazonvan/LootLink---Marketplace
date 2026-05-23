"""
P1-15: функциональные индексы LOWER(username) и LOWER(email).

Чтобы `username__iexact` и `email__iexact` использовали B-tree индекс
вместо Seq Scan. Для PostgreSQL — CREATE INDEX ON ... (LOWER(field)).
Для SQLite — индексы создаются без функции (Django fallback).
"""

from django.db import migrations
from django.db.models import F
from django.db.models.functions import Lower


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0021_customuser_soft_delete"),
    ]

    operations = [
        migrations.RunSQL(
            sql=[
                "CREATE INDEX IF NOT EXISTS accounts_customuser_username_lower_idx "
                "ON accounts_customuser (LOWER(username));",
                "CREATE INDEX IF NOT EXISTS accounts_customuser_email_lower_idx "
                "ON accounts_customuser (LOWER(email));",
            ],
            reverse_sql=[
                "DROP INDEX IF EXISTS accounts_customuser_username_lower_idx;",
                "DROP INDEX IF EXISTS accounts_customuser_email_lower_idx;",
            ],
        ),
    ]
