#!/bin/bash
# ========================================
# AWS SES AUTOMATIC SETUP FOR LOOTLINK
# ========================================

echo "========================================"
echo "  AWS SES SETUP FOR LOOTLINK"
echo "========================================"
echo ""

# Проверка
if [ ! -f "manage.py" ]; then
    echo "Error: Run from /opt/lootlink directory!"
    exit 1
fi

echo "Этот скрипт настроит AWS SES для отправки email."
echo ""
echo "Вам понадобится:"
echo "  1. AWS Access Key ID (SMTP Username)"
echo "  2. AWS Secret Access Key (SMTP Password)"
echo "  3. Верифицированный email в SES"
echo ""
read -p "Продолжить? (y/n): " continue_setup

if [ "$continue_setup" != "y" ]; then
    echo "Отменено"
    exit 0
fi

# Получаем данные
echo ""
echo "=== AWS CREDENTIALS ==="
read -p "AWS Access Key ID (AKIAXXXXXXX): " aws_key_id
read -sp "AWS Secret Access Key (длинный ключ): " aws_secret_key
echo ""
read -p "AWS Region (по умолчанию eu-west-1): " aws_region
aws_region=${aws_region:-eu-west-1}

read -p "FROM email (верифицированный в SES): " from_email

# Установка пакета
echo ""
echo "=== INSTALLING DJANGO-SES ==="
source venv/bin/activate
pip install django-ses boto3 --quiet

if [ $? -eq 0 ]; then
    echo "✅ django-ses установлен"
else
    echo "❌ Ошибка установки django-ses"
    exit 1
fi

# Обновление .env
echo ""
echo "=== UPDATING .env ==="

# Backup
cp .env .env.backup_$(date +%Y%m%d_%H%M%S)

# Удаляем старые EMAIL настройки
sed -i '/^EMAIL_BACKEND=/d' .env
sed -i '/^EMAIL_HOST=/d' .env
sed -i '/^EMAIL_PORT=/d' .env
sed -i '/^EMAIL_USE_TLS=/d' .env
sed -i '/^EMAIL_USE_SSL=/d' .env
sed -i '/^EMAIL_HOST_USER=/d' .env
sed -i '/^EMAIL_HOST_PASSWORD=/d' .env
sed -i '/^DEFAULT_FROM_EMAIL=/d' .env
sed -i '/^AWS_ACCESS_KEY_ID=/d' .env
sed -i '/^AWS_SECRET_ACCESS_KEY=/d' .env
sed -i '/^AWS_SES_REGION/d' .env
sed -i '/^SENDGRID/d' .env

# Добавляем новые
cat >> .env << EOF

# ========================================
# EMAIL - AWS SES (Production Ready)
# ========================================
EMAIL_BACKEND=django_ses.SESBackend
AWS_ACCESS_KEY_ID=$aws_key_id
AWS_SECRET_ACCESS_KEY=$aws_secret_key
AWS_SES_REGION_NAME=$aws_region
AWS_SES_REGION_ENDPOINT=email.$aws_region.amazonaws.com
DEFAULT_FROM_EMAIL=$from_email
EOF

echo "✅ .env обновлен"

# Обновление requirements.txt
if ! grep -q "django-ses" requirements.txt; then
    echo "django-ses>=3.5.0" >> requirements.txt
    echo "✅ requirements.txt обновлен"
fi

# Перезапуск Django
echo ""
echo "=== RESTARTING DJANGO ==="
sudo systemctl restart lootlink

sleep 2

if systemctl is-active --quiet lootlink; then
    echo "✅ Django перезапущен"
else
    echo "❌ Ошибка перезапуска Django"
    echo "Проверьте: sudo journalctl -u lootlink -n 50"
    exit 1
fi

# Тестирование
echo ""
echo "========================================"
echo "  TESTING EMAIL SENDING"
echo "========================================"
echo ""

read -p "Введите email для теста (ваш Gmail): " test_email

source venv/bin/activate
python manage.py shell << PYEOF
from django.core.mail import send_mail
from django.conf import settings

print('Отправка тестового письма...')
print(f'От: {settings.DEFAULT_FROM_EMAIL}')
print(f'Кому: $test_email')
print()

try:
    send_mail(
        subject='[ТЕСТ] AWS SES работает! 🚀',
        message='''Поздравляем!

AWS SES настроен и работает идеально!

Теперь ваш сайт LootLink может отправлять:
✅ До 62,000 писем/месяц БЕСПЛАТНО (если на AWS EC2)
✅ Или \$0.10 за 1,000 писем (очень дешево!)
✅ Неограниченное количество при масштабировании
✅ 99.9% доставляемость
✅ Молниеносная скорость отправки

Ваш сайт готов к десяткам тысяч пользователей!

С уважением,
Команда LootLink
        ''',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=['$test_email'],
        fail_silently=False
    )
    print('✅ УСПЕХ! Письмо отправлено!')
    print()
    print('Проверьте почту: $test_email')
    print('(если не пришло - проверьте SPAM)')
    
except Exception as e:
    print(f'❌ ОШИБКА: {e}')
    print()
    print('Возможные причины:')
    print('1. SES в Sandbox mode - верифицируйте получателя в SES Console')
    print('2. Неверные credentials')
    print('3. Регион не совпадает')
    import traceback
    traceback.print_exc()
PYEOF

echo ""
echo "========================================"
echo "SETUP COMPLETE!"
echo "========================================"
echo ""
echo "Если письмо не пришло:"
echo "  1. Проверьте что в SES Console:"
echo "     - Email reazonvan@ya.ru верифицирован (статус: Verified)"
echo "     - Sandbox mode: верифицируйте $test_email или запросите Production Access"
echo "  2. Логи: sudo journalctl -u lootlink -n 100 | grep -i email"
echo ""
echo "После одобрения Production Access (24 часа):"
echo "  - Сможете отправлять на ЛЮБЫЕ email"
echo "  - Готовы к десяткам тысяч пользователей"
echo ""

