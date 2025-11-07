# Generated manually for performance optimization

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('transactions', '0003_alter_review_options_and_more'),  # Замените на последнюю миграцию
    ]

    operations = [
        # PurchaseRequest indexes
        migrations.AddIndex(
            model_name='purchaserequest',
            index=models.Index(
                fields=['buyer', 'status'],
                name='pr_buyer_status_idx'
            ),
        ),
        migrations.AddIndex(
            model_name='purchaserequest',
            index=models.Index(
                fields=['seller', 'status'],
                name='pr_seller_status_idx'
            ),
        ),
        migrations.AddIndex(
            model_name='purchaserequest',
            index=models.Index(
                fields=['listing', 'status'],
                name='pr_listing_status_idx'
            ),
        ),
        
        # Review indexes
        migrations.AddIndex(
            model_name='review',
            index=models.Index(
                fields=['reviewed_user', '-created_at'],
                name='review_user_created_idx'
            ),
        ),
        migrations.AddIndex(
            model_name='review',
            index=models.Index(
                fields=['reviewer', '-created_at'],
                name='review_reviewer_idx'
            ),
        ),
    ]

