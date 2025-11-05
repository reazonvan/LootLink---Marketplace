# Generated migration for last_seen field
from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0011_profile_is_moderator'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='last_seen',
            field=models.DateTimeField(
                default=django.utils.timezone.now,
                verbose_name='Последняя активность',
                help_text='Автоматически обновляется при каждом запросе'
            ),
        ),
        migrations.AddIndex(
            model_name='profile',
            index=models.Index(fields=['last_seen'], name='profile_last_seen_idx'),
        ),
    ]

