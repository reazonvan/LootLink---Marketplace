# Generated manually for performance optimization

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0007_alter_conversation_unique_together_and_more'),  # Замените на последнюю миграцию
    ]

    operations = [
        # Message indexes для быстрого получения сообщений
        migrations.AddIndex(
            model_name='message',
            index=models.Index(
                fields=['conversation', 'created_at'],
                name='msg_conv_created_idx'
            ),
        ),
        migrations.AddIndex(
            model_name='message',
            index=models.Index(
                fields=['conversation', 'is_read'],
                name='msg_conv_read_idx'
            ),
        ),
        
        # Conversation indexes
        migrations.AddIndex(
            model_name='conversation',
            index=models.Index(
                fields=['participant1', '-updated_at'],
                name='conv_p1_updated_idx'
            ),
        ),
        migrations.AddIndex(
            model_name='conversation',
            index=models.Index(
                fields=['participant2', '-updated_at'],
                name='conv_p2_updated_idx'
            ),
        ),
    ]

