# Generated migration for PostgreSQL Full-Text Search

from django.contrib.postgres.search import SearchVector
from django.contrib.postgres.indexes import GinIndex
from django.db import migrations, models
from django.contrib.postgres.search import SearchVectorField


def compute_search_vector(apps, schema_editor):
    """Заполняем search_vector для существующих объявлений."""
    Listing = apps.get_model('listings', 'Listing')
    Listing.objects.update(
        search_vector=SearchVector('title', weight='A', config='russian') + 
                     SearchVector('description', weight='B', config='russian')
    )


class Migration(migrations.Migration):

    dependencies = [
        ('listings', '0007_add_performance_indexes'),
    ]

    operations = [
        # Добавляем поле для full-text search
        migrations.AddField(
            model_name='listing',
            name='search_vector',
            field=SearchVectorField(null=True, editable=False),
        ),
        
        # Добавляем GIN индекс для поиска
        migrations.AddIndex(
            model_name='listing',
            index=GinIndex(fields=['search_vector'], name='listing_search_vector_idx'),
        ),
        
        # Заполняем search_vector для существующих записей
        migrations.RunPython(compute_search_vector, reverse_code=migrations.RunPython.noop),
    ]

