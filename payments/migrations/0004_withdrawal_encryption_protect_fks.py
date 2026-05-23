"""
P0-фикс:
- Расширяем Withdrawal.payment_details до 512 (зашифрованные данные)
- Добавляем Withdrawal.payment_details_masked для безопасного UI
- Меняем on_delete=CASCADE → PROTECT для финансовых моделей
  (защита истории при удалении пользователя/листинга).
"""

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("payments", "0003_escrow_escrow_status_deadline_idx_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name="withdrawal",
            name="payment_details",
            field=models.CharField(
                help_text="Зашифрованные реквизиты получателя",
                max_length=512,
                verbose_name="Реквизиты (зашифровано)",
            ),
        ),
        migrations.AddField(
            model_name="withdrawal",
            name="payment_details_masked",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Безопасное представление для UI: **** 1234",
                max_length=64,
                verbose_name="Маскированные реквизиты",
            ),
        ),
        migrations.AlterField(
            model_name="withdrawal",
            name="user",
            field=models.ForeignKey(
                on_delete=models.deletion.PROTECT,
                related_name="withdrawals",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Пользователь",
            ),
        ),
        migrations.AlterField(
            model_name="escrow",
            name="buyer",
            field=models.ForeignKey(
                on_delete=models.deletion.PROTECT,
                related_name="escrow_as_buyer",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Покупатель",
            ),
        ),
        migrations.AlterField(
            model_name="escrow",
            name="seller",
            field=models.ForeignKey(
                on_delete=models.deletion.PROTECT,
                related_name="escrow_as_seller",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Продавец",
            ),
        ),
        migrations.AlterField(
            model_name="wallet",
            name="user",
            field=models.OneToOneField(
                on_delete=models.deletion.PROTECT,
                related_name="wallet",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Пользователь",
            ),
        ),
        migrations.AlterField(
            model_name="transaction",
            name="user",
            field=models.ForeignKey(
                on_delete=models.deletion.PROTECT,
                related_name="transactions",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Пользователь",
            ),
        ),
    ]
