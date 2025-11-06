# Generated manually to remove social network fields

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0013_remove_profile_profile_last_seen_idx'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='profile',
            name='telegram',
        ),
        migrations.RemoveField(
            model_name='profile',
            name='discord',
        ),
    ]

