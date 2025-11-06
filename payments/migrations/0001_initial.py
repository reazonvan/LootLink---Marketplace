# Generated migration for payments app
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.core.validators


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('transactions', '0004_remove_purchaserequest_purchase_buyer_status_idx_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='Wallet',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('balance', models.DecimalField(decimal_places=2, default=0.0, max_digits=10, validators=[django.core.validators.MinValueValidator(0)], verbose_name='Баланс')),
                ('frozen_balance', models.DecimalField(decimal_places=2, default=0.0, help_text='Средства в эскроу', max_digits=10, validators=[django.core.validators.MinValueValidator(0)], verbose_name='Замороженный баланс')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Дата обновления')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='wallet', to=settings.AUTH_USER_MODEL, verbose_name='Пользователь')),
            ],
            options={
                'verbose_name': 'Кошелек',
                'verbose_name_plural': 'Кошельки',
            },
        ),
        migrations.CreateModel(
            name='Transaction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('transaction_type', models.CharField(choices=[('deposit', 'Пополнение'), ('withdrawal', 'Вывод'), ('purchase', 'Покупка'), ('sale', 'Продажа'), ('refund', 'Возврат'), ('escrow_freeze', 'Заморозка (эскроу)'), ('escrow_release', 'Разморозка (эскроу)'), ('commission', 'Комиссия'), ('promo', 'Промокод')], max_length=20, verbose_name='Тип транзакции')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Сумма')),
                ('status', models.CharField(choices=[('pending', 'Ожидает'), ('processing', 'Обработка'), ('completed', 'Завершена'), ('failed', 'Ошибка'), ('cancelled', 'Отменена')], default='pending', max_length=20, verbose_name='Статус')),
                ('description', models.TextField(blank=True, verbose_name='Описание')),
                ('payment_system', models.CharField(blank=True, help_text='ЮKassa, Stripe и т.д.', max_length=50, verbose_name='Платежная система')),
                ('payment_id', models.CharField(blank=True, max_length=255, verbose_name='ID платежа в системе')),
                ('payment_data', models.JSONField(blank=True, default=dict, verbose_name='Данные платежа')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Дата создания')),
                ('completed_at', models.DateTimeField(blank=True, null=True, verbose_name='Дата завершения')),
                ('purchase_request', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='transactions', to='transactions.purchaserequest', verbose_name='Запрос на покупку')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='transactions', to=settings.AUTH_USER_MODEL, verbose_name='Пользователь')),
            ],
            options={
                'verbose_name': 'Транзакция',
                'verbose_name_plural': 'Транзакции',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='PromoCode',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=50, unique=True, verbose_name='Код')),
                ('discount_type', models.CharField(choices=[('fixed', 'Фиксированная сумма'), ('percent', 'Процент')], default='percent', max_length=20, verbose_name='Тип скидки')),
                ('discount_value', models.DecimalField(decimal_places=2, max_digits=10, validators=[django.core.validators.MinValueValidator(0)], verbose_name='Значение скидки')),
                ('min_purchase_amount', models.DecimalField(decimal_places=2, default=0, max_digits=10, validators=[django.core.validators.MinValueValidator(0)], verbose_name='Минимальная сумма покупки')),
                ('max_uses', models.PositiveIntegerField(blank=True, help_text='Оставьте пустым для неограниченного', null=True, verbose_name='Максимум использований')),
                ('uses_count', models.PositiveIntegerField(default=0, verbose_name='Использовано раз')),
                ('valid_from', models.DateTimeField(verbose_name='Действителен с')),
                ('valid_until', models.DateTimeField(verbose_name='Действителен до')),
                ('is_active', models.BooleanField(default=True, verbose_name='Активен')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')),
            ],
            options={
                'verbose_name': 'Промокод',
                'verbose_name_plural': 'Промокоды',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='Withdrawal',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, help_text='Минимум 100 ₽', max_digits=10, validators=[django.core.validators.MinValueValidator(100)], verbose_name='Сумма')),
                ('payment_method', models.CharField(choices=[('card', 'Банковская карта'), ('yoomoney', 'ЮMoney'), ('qiwi', 'QIWI'), ('webmoney', 'WebMoney')], max_length=20, verbose_name='Способ вывода')),
                ('payment_details', models.CharField(help_text='Номер карты, кошелька и т.д.', max_length=255, verbose_name='Реквизиты')),
                ('status', models.CharField(choices=[('pending', 'Ожидает'), ('processing', 'Обработка'), ('completed', 'Завершен'), ('rejected', 'Отклонен')], default='pending', max_length=20, verbose_name='Статус')),
                ('admin_comment', models.TextField(blank=True, verbose_name='Комментарий администратора')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')),
                ('processed_at', models.DateTimeField(blank=True, null=True, verbose_name='Дата обработки')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='withdrawals', to=settings.AUTH_USER_MODEL, verbose_name='Пользователь')),
            ],
            options={
                'verbose_name': 'Вывод средств',
                'verbose_name_plural': 'Выводы средств',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='Escrow',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10, validators=[django.core.validators.MinValueValidator(0)], verbose_name='Сумма')),
                ('status', models.CharField(choices=[('created', 'Создан'), ('funded', 'Средства заморожены'), ('released', 'Средства переведены продавцу'), ('refunded', 'Возврат покупателю'), ('disputed', 'Спор')], default='created', max_length=20, verbose_name='Статус')),
                ('auto_release_days', models.PositiveIntegerField(default=3, help_text='Через сколько дней автоматически передать средства продавцу', verbose_name='Авто-освобождение (дней)')),
                ('release_deadline', models.DateTimeField(blank=True, null=True, verbose_name='Дедлайн освобождения')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')),
                ('funded_at', models.DateTimeField(blank=True, null=True, verbose_name='Дата заморозки средств')),
                ('released_at', models.DateTimeField(blank=True, null=True, verbose_name='Дата освобождения средств')),
                ('buyer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='escrow_as_buyer', to=settings.AUTH_USER_MODEL, verbose_name='Покупатель')),
                ('purchase_request', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='escrow', to='transactions.purchaserequest', verbose_name='Запрос на покупку')),
                ('seller', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='escrow_as_seller', to=settings.AUTH_USER_MODEL, verbose_name='Продавец')),
            ],
            options={
                'verbose_name': 'Эскроу',
                'verbose_name_plural': 'Эскроу',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='transaction',
            index=models.Index(fields=['user', '-created_at'], name='payments_tr_user_id_a4b8d9_idx'),
        ),
        migrations.AddIndex(
            model_name='transaction',
            index=models.Index(fields=['status', '-created_at'], name='payments_tr_status_c8e9f1_idx'),
        ),
        migrations.AddIndex(
            model_name='transaction',
            index=models.Index(fields=['payment_id'], name='payments_tr_payment_d2a3c4_idx'),
        ),
    ]

