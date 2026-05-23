"""
P0-фикс: snapshot цены сделки + PROTECT FK на критических связях.

- Добавляет PurchaseRequest.amount — фиксирует цену listing при создании
  запроса. Эскроу фондируется из этого поля, а не из listing.price.
- Меняет on_delete с CASCADE на PROTECT для buyer/seller/listing, чтобы
  удаление пользователя или листинга не убивало историю сделок и эскроу.
- Backfill: для существующих PurchaseRequest копирует listing.price.
- Добавляет статус 'disputed'.
"""

from django.conf import settings
from django.db import migrations, models


def backfill_amount(apps, schema_editor):
    PurchaseRequest = apps.get_model("transactions", "PurchaseRequest")
    # Заполняем amount значением listing.price, если ещё не заполнено.
    for pr in PurchaseRequest.objects.filter(amount__isnull=True).select_related("listing"):
        pr.amount = pr.listing.price
        pr.save(update_fields=["amount"])


def noop_reverse(apps, schema_editor):
    """Откат backfill — обнуляем amount."""
    PurchaseRequest = apps.get_model("transactions", "PurchaseRequest")
    PurchaseRequest.objects.update(amount=None)


class Migration(migrations.Migration):

    dependencies = [
        ("listings", "0018_category_funpay_id_game_funpay_id"),
        ("transactions", "0009_remove_disputemessage_dispute_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="purchaserequest",
            name="amount",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text=(
                    "Snapshot цены listing на момент создания запроса. "
                    "Эскроу фондируется именно на эту сумму."
                ),
                max_digits=12,
                null=True,
                verbose_name="Сумма сделки",
            ),
        ),
        migrations.RunPython(backfill_amount, reverse_code=noop_reverse),
        migrations.AlterField(
            model_name="purchaserequest",
            name="listing",
            field=models.ForeignKey(
                help_text=(
                    "PROTECT: листинг с покупками нельзя удалить — " "историю нужно сохранять."
                ),
                on_delete=models.deletion.PROTECT,
                related_name="purchase_requests",
                to="listings.listing",
                verbose_name="Объявление",
            ),
        ),
        migrations.AlterField(
            model_name="purchaserequest",
            name="buyer",
            field=models.ForeignKey(
                on_delete=models.deletion.PROTECT,
                related_name="purchases",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Покупатель",
            ),
        ),
        migrations.AlterField(
            model_name="purchaserequest",
            name="seller",
            field=models.ForeignKey(
                on_delete=models.deletion.PROTECT,
                related_name="sales",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Продавец",
            ),
        ),
        migrations.AlterField(
            model_name="purchaserequest",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending", "Ожидает подтверждения"),
                    ("accepted", "Принят"),
                    ("rejected", "Отклонен"),
                    ("completed", "Завершен"),
                    ("cancelled", "Отменен"),
                    ("disputed", "Спор"),
                ],
                db_index=True,
                default="pending",
                max_length=20,
                verbose_name="Статус",
            ),
        ),
    ]
