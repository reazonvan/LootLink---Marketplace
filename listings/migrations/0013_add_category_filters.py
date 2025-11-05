# Generated migration for category filters system
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('listings', '0011_alter_game_options_game_order'),
    ]

    operations = [
        migrations.CreateModel(
            name='CategoryFilter',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='Например: Ранг, Редкость, Количество кубков', max_length=100, verbose_name='Название фильтра')),
                ('field_name', models.CharField(help_text='Техническое имя (латиница, без пробелов). Например: rank, rarity, trophies', max_length=100, verbose_name='Имя поля')),
                ('filter_type', models.CharField(choices=[('select', 'Выбор из списка'), ('multiselect', 'Множественный выбор'), ('range', 'Диапазон (от-до)'), ('checkbox', 'Чекбокс (да/нет)')], default='select', max_length=20, verbose_name='Тип фильтра')),
                ('order', models.PositiveIntegerField(default=0, help_text='Меньше число = выше в списке фильтров', verbose_name='Порядок сортировки')),
                ('is_required', models.BooleanField(default=False, help_text='Требовать заполнение при создании объявления', verbose_name='Обязательный фильтр')),
                ('is_active', models.BooleanField(default=True, verbose_name='Активен')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')),
                ('category', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='filters', to='listings.category', verbose_name='Категория')),
            ],
            options={
                'verbose_name': 'Фильтр категории',
                'verbose_name_plural': 'Фильтры категорий',
                'ordering': ['category', 'order', 'name'],
                'unique_together': {('category', 'field_name')},
                'indexes': [
                    models.Index(fields=['category', 'is_active'], name='category_filter_cat_active_idx'),
                    models.Index(fields=['category', 'order'], name='category_filter_cat_order_idx'),
                ],
            },
        ),
        migrations.CreateModel(
            name='FilterOption',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('value', models.CharField(help_text='Например: Global Elite, Arcana, 30000+', max_length=100, verbose_name='Значение')),
                ('display_name', models.CharField(blank=True, help_text='Если пусто, используется value', max_length=100, verbose_name='Отображаемое имя')),
                ('order', models.PositiveIntegerField(default=0, verbose_name='Порядок')),
                ('is_active', models.BooleanField(default=True, verbose_name='Активна')),
                ('filter', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='options', to='listings.categoryfilter', verbose_name='Фильтр')),
            ],
            options={
                'verbose_name': 'Опция фильтра',
                'verbose_name_plural': 'Опции фильтров',
                'ordering': ['filter', 'order', 'value'],
                'unique_together': {('filter', 'value')},
            },
        ),
        migrations.CreateModel(
            name='ListingFilterValue',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('value_text', models.CharField(blank=True, max_length=200, verbose_name='Текстовое значение')),
                ('value_int', models.IntegerField(blank=True, null=True, verbose_name='Числовое значение')),
                ('value_bool', models.BooleanField(blank=True, null=True, verbose_name='Булевое значение')),
                ('category_filter', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='listing_values', to='listings.categoryfilter', verbose_name='Фильтр')),
                ('listing', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='filter_values', to='listings.listing', verbose_name='Объявление')),
                ('selected_options', models.ManyToManyField(blank=True, related_name='selected_in_listings', to='listings.filteroption', verbose_name='Выбранные опции')),
            ],
            options={
                'verbose_name': 'Значение фильтра объявления',
                'verbose_name_plural': 'Значения фильтров объявлений',
                'unique_together': {('listing', 'category_filter')},
                'indexes': [
                    models.Index(fields=['listing', 'category_filter'], name='listing_filter_idx'),
                    models.Index(fields=['category_filter', 'value_text'], name='filter_value_text_idx'),
                    models.Index(fields=['category_filter', 'value_int'], name='filter_value_int_idx'),
                ],
            },
        ),
    ]

