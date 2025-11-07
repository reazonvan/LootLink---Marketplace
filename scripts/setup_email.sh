#!/bin/bash
# ========================================
# EMAIL SETUP SCRIPT FOR LOOTLINK
# ========================================
# Автоматическая настройка email для production
# ========================================

echo "========================================"
echo "  EMAIL SETUP FOR LOOTLINK"
echo "========================================"
echo ""

# Проверка что мы в правильной директории
if [ ! -f "manage.py" ]; then
    echo "Error: Run this script from /opt/lootlink directory!"
    exit 1
fi

# Проверка наличия .env
if [ ! -f ".env" ]; then
    echo "Error: .env file not found!"
    exit 1
fi

echo "Выберите email провайдера:"
echo "1) Yandex Mail (Рекомендуется для России)"
echo "2) Mail.ru"
echo "3) Gmail"
echo "4) SendGrid API"
echo "5) Ручная настройка"
echo ""
read -p "Введите номер (1-5): " provider_choice

case $provider_choice in
    1)
        echo ""
        echo "=== НАСТРОЙКА YANDEX MAIL ==="
        EMAIL_HOST="smtp.yandex.ru"
        EMAIL_PORT=587
        EMAIL_USE_TLS=True
        EMAIL_USE_SSL=False
        
        read -p "Введите email (например: lootlink@yandex.ru): " EMAIL_USER
        read -sp "Введите пароль приложения: " EMAIL_PASS
        echo ""
        ;;
    2)
        echo ""
        echo "=== НАСТРОЙКА MAIL.RU ==="
        EMAIL_HOST="smtp.mail.ru"
        EMAIL_PORT=465
        EMAIL_USE_TLS=False
        EMAIL_USE_SSL=True
        
        read -p "Введите email (например: lootlink@mail.ru): " EMAIL_USER
        read -sp "Введите пароль: " EMAIL_PASS
        echo ""
        ;;
    3)
        echo ""
        echo "=== НАСТРОЙКА GMAIL ==="
        EMAIL_HOST="smtp.gmail.com"
        EMAIL_PORT=587
        EMAIL_USE_TLS=True
        EMAIL_USE_SSL=False
        
        read -p "Введите Gmail: " EMAIL_USER
        read -sp "Введите App Password (16 символов): " EMAIL_PASS
        echo ""
        ;;
    4)
        echo ""
        echo "=== НАСТРОЙКА SENDGRID ==="
        read -p "Введите SendGrid API Key: " SENDGRID_KEY
        read -p "Введите FROM email: " EMAIL_USER
        
        # Для SendGrid нужен другой backend
        sed -i "s|EMAIL_BACKEND=.*|EMAIL_BACKEND=sendgrid_backend.SendgridBackend|" .env
        sed -i "s|SENDGRID_API_KEY=.*|SENDGRID_API_KEY=$SENDGRID_KEY|" .env
        sed -i "s|DEFAULT_FROM_EMAIL=.*|DEFAULT_FROM_EMAIL=$EMAIL_USER|" .env
        
        echo "SendGrid настроен! Установите: pip install sendgrid-django"
        exit 0
        ;;
    5)
        echo "Отредактируйте .env вручную"
        exit 0
        ;;
    *)
        echo "Неверный выбор"
        exit 1
        ;;
esac

# Обновляем .env файл
echo ""
echo "Обновляем .env..."

sed -i "s|EMAIL_BACKEND=.*|EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend|" .env
sed -i "s|EMAIL_HOST=.*|EMAIL_HOST=$EMAIL_HOST|" .env
sed -i "s|EMAIL_PORT=.*|EMAIL_PORT=$EMAIL_PORT|" .env
sed -i "s|EMAIL_USE_TLS=.*|EMAIL_USE_TLS=$EMAIL_USE_TLS|" .env
sed -i "s|EMAIL_HOST_USER=.*|EMAIL_HOST_USER=$EMAIL_USER|" .env
sed -i "s|EMAIL_HOST_PASSWORD=.*|EMAIL_HOST_PASSWORD=$EMAIL_PASS|" .env
sed -i "s|DEFAULT_FROM_EMAIL=.*|DEFAULT_FROM_EMAIL=LootLink <$EMAIL_USER>|" .env

echo "✅ .env обновлен"

# Перезапускаем Django
echo ""
echo "Перезапускаем Django..."
sudo systemctl restart lootlink

sleep 2

# Тестируем отправку
echo ""
echo "========================================"
echo "  ТЕСТИРОВАНИЕ EMAIL"
echo "========================================"
echo ""

read -p "Введите email для теста (куда отправить тестовое письмо): " test_email

source venv/bin/activate
python manage.py shell << EOF
from django.core.mail import send_mail
from django.conf import settings

try:
    send_mail(
        '[TEST] LootLink Email Configuration',
        'Поздравляем! Email настроен правильно и работает!\\n\\nТеперь пользователи будут получать:\\n- Коды сброса пароля\\n- Ссылки верификации\\n- Уведомления о покупках\\n\\nС уважением,\\nКоманда LootLink',
        settings.DEFAULT_FROM_EMAIL,
        ['$test_email'],
        fail_silently=False
    )
    print('\\n✅ УСПЕХ! Тестовое письмо отправлено на $test_email')
    print('Проверьте почту (возможно в папке SPAM)')
except Exception as e:
    print(f'\\n❌ ОШИБКА: {e}')
    print('\\nПроверьте:')
    print('1. Правильность логина/пароля')
    print('2. Что используется пароль приложения (не основной пароль)')
    print('3. Что 2FA включена на email аккаунте')
EOF

echo ""
echo "========================================"
echo "НАСТРОЙКА ЗАВЕРШЕНА!"
echo "========================================"
echo ""
echo "Проверьте почту $test_email"
echo "Если письмо не пришло - проверьте папку SPAM"
echo ""
echo "Логи Django: sudo journalctl -u lootlink -n 50"
echo ""

