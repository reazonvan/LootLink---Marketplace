"""P2-13: счётчик попыток ввода кода сброса пароля."""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0022_username_email_lower_index"),
    ]

    operations = [
        migrations.AddField(
            model_name="passwordresetcode",
            name="attempts",
            field=models.PositiveIntegerField(
                default=0,
                help_text="Защита от брутфорса 8-символьного кода (P2-13)",
                verbose_name="Количество попыток ввода",
            ),
        ),
    ]
