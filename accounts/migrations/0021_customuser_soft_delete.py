"""
P0-22: soft-delete для CustomUser (152-ФЗ/GDPR "право на забвение").

Поля is_deleted + deleted_at позволяют анонимизировать аккаунт без
жёсткого удаления, что было бы запрещено FK PROTECT на финансовых
моделях (Wallet, Transaction, Escrow, PurchaseRequest).
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0020_remove_profile_balance"),
    ]

    operations = [
        migrations.AddField(
            model_name="customuser",
            name="is_deleted",
            field=models.BooleanField(
                db_index=True,
                default=False,
                help_text="Soft-delete: данные анонимизированы.",
                verbose_name="Удалён",
            ),
        ),
        migrations.AddField(
            model_name="customuser",
            name="deleted_at",
            field=models.DateTimeField(
                blank=True,
                null=True,
                verbose_name="Дата удаления",
            ),
        ),
    ]
