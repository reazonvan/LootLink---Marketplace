# Generated migration for adding performance indexes

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0003_alter_message_options'),
    ]

    operations = [
        # Добавляем составные индексы для Conversation
        migrations.AddIndex(
            model_name='conversation',
            index=models.Index(fields=['participant1', '-updated_at'], name='conv_p1_updated_idx'),
        ),
        migrations.AddIndex(
            model_name='conversation',
            index=models.Index(fields=['participant2', '-updated_at'], name='conv_p2_updated_idx'),
        ),
        migrations.AddIndex(
            model_name='conversation',
            index=models.Index(fields=['listing', '-updated_at'], name='conv_listing_updated_idx'),
        ),
        
        # Добавляем индексы для Message
        migrations.AddIndex(
            model_name='message',
            index=models.Index(fields=['conversation', 'created_at'], name='message_conv_created_idx'),
        ),
        migrations.AddIndex(
            model_name='message',
            index=models.Index(fields=['conversation', 'is_read'], name='message_conv_read_idx'),
        ),
        migrations.AddIndex(
            model_name='message',
            index=models.Index(fields=['sender', '-created_at'], name='message_sender_created_idx'),
        ),
    ]

