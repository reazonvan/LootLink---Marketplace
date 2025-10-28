# Generated migration for adding performance indexes

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('transactions', '0002_alter_purchaserequest_status'),
    ]

    operations = [
        # Добавляем составные индексы для PurchaseRequest
        migrations.AddIndex(
            model_name='purchaserequest',
            index=models.Index(fields=['buyer', 'status', '-created_at'], name='purchase_buyer_status_idx'),
        ),
        migrations.AddIndex(
            model_name='purchaserequest',
            index=models.Index(fields=['seller', 'status', '-created_at'], name='purchase_seller_status_idx'),
        ),
        migrations.AddIndex(
            model_name='purchaserequest',
            index=models.Index(fields=['listing', 'status'], name='purchase_listing_status_idx'),
        ),
        migrations.AddIndex(
            model_name='purchaserequest',
            index=models.Index(fields=['status', '-created_at'], name='purchase_status_created_idx'),
        ),
        
        # Добавляем индексы для Review
        migrations.AddIndex(
            model_name='review',
            index=models.Index(fields=['reviewed_user', '-created_at'], name='review_user_created_idx'),
        ),
        migrations.AddIndex(
            model_name='review',
            index=models.Index(fields=['reviewer', '-created_at'], name='review_reviewer_created_idx'),
        ),
    ]

