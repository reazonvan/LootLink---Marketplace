# Generated migration for conversation ordering constraint
from django.db import migrations, models
from django.db.models import Q, CheckConstraint


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0005_remove_conversation_conv_p1_updated_idx_and_more'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='conversation',
            constraint=CheckConstraint(
                check=Q(participant1_id__lt=models.F('participant2_id')),
                name='participant1_less_than_participant2',
                violation_error_message='participant1 должен быть меньше participant2 (сортировка по ID)'
            ),
        ),
    ]

