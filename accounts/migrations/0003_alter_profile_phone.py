# Generated migration for phone field unique constraint

from django.db import migrations, models


def convert_empty_to_null(apps, schema_editor):
    """Конвертирует пустые строки в NULL для phone."""
    Profile = apps.get_model('accounts', 'Profile')
    Profile.objects.filter(phone='').update(phone=None)


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_profile_is_verified_profile_verification_date'),
    ]

    operations = [
        # Сначала разрешаем NULL
        migrations.AlterField(
            model_name='profile',
            name='phone',
            field=models.CharField(blank=True, max_length=20, null=True, verbose_name='Телефон'),
        ),
        # Затем конвертируем пустые строки в NULL
        migrations.RunPython(convert_empty_to_null, migrations.RunPython.noop),
        # И наконец добавляем unique
        migrations.AlterField(
            model_name='profile',
            name='phone',
            field=models.CharField(blank=True, max_length=20, null=True, unique=True, verbose_name='Телефон'),
        ),
    ]

