# Generated migration for adding performance indexes

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('listings', '0006_alter_listing_description_alter_listing_image'),
    ]

    operations = [
        # Добавляем составные индексы для Listing
        migrations.AddIndex(
            model_name='listing',
            index=models.Index(fields=['game', 'status', '-created_at'], name='listing_game_status_created_idx'),
        ),
        migrations.AddIndex(
            model_name='listing',
            index=models.Index(fields=['seller', 'status', '-created_at'], name='listing_seller_status_idx'),
        ),
        migrations.AddIndex(
            model_name='listing',
            index=models.Index(fields=['status', '-price'], name='listing_status_price_idx'),
        ),
        migrations.AddIndex(
            model_name='listing',
            index=models.Index(fields=['status', '-created_at'], name='listing_status_created_idx'),
        ),
    ]

