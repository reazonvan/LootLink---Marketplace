# Generated migration for adding performance indexes

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0007_alter_profile_avatar'),
    ]

    operations = [
        # Добавляем составные индексы для Profile
        migrations.AddIndex(
            model_name='profile',
            index=models.Index(fields=['user', 'rating'], name='profile_user_rating_idx'),
        ),
        migrations.AddIndex(
            model_name='profile',
            index=models.Index(fields=['is_verified', 'rating'], name='profile_verified_rating_idx'),
        ),
        migrations.AddIndex(
            model_name='profile',
            index=models.Index(fields=['-rating', '-total_sales'], name='profile_top_sellers_idx'),
        ),
    ]

