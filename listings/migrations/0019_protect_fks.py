"""
P0-21: PROTECT для Listing.seller и Listing.game.

Защищает историю продаж — нельзя удалить пользователя/игру с активными
листингами, нужно сначала разрулить связи (анонимизация vs удаление).
"""

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("listings", "0018_category_funpay_id_game_funpay_id"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name="listing",
            name="seller",
            field=models.ForeignKey(
                help_text=(
                    "PROTECT: история продаж не должна теряться при " "анонимизации пользователя."
                ),
                on_delete=models.deletion.PROTECT,
                related_name="listings",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Продавец",
            ),
        ),
        migrations.AlterField(
            model_name="listing",
            name="game",
            field=models.ForeignKey(
                on_delete=models.deletion.PROTECT,
                related_name="listings",
                to="listings.game",
                verbose_name="Игра",
            ),
        ),
    ]
