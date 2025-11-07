# Generated manually for performance optimization

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('listings', '0013_add_category_filters'),
    ]

    operations = [
        # Composite index для фильтрации по game + category + status
        migrations.AddIndex(
            model_name='listing',
            index=models.Index(
                fields=['game', 'category', 'status'],
                name='listing_gcs_idx'
            ),
        ),
        # Composite index для списков с сортировкой
        migrations.AddIndex(
            model_name='listing',
            index=models.Index(
                fields=['game', 'status', '-created_at'],
                name='listing_gsc_idx'
            ),
        ),
        # Index для поиска по продавцу
        migrations.AddIndex(
            model_name='listing',
            index=models.Index(
                fields=['seller', 'status', '-created_at'],
                name='listing_ssc_idx'
            ),
        ),
    ]

