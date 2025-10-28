# Скрипт для исправления проблем на сервере
# Использование: .\deploy_fix.ps1

$SERVER = "root@91.218.245.178"
$PASSWORD = "BWJ_1anRP0"
$PROJECT_PATH = "/opt/lootlink"

Write-Host "=== ИСПРАВЛЕНИЕ ПРОБЛЕМ НА СЕРВЕРЕ ===" -ForegroundColor Green
Write-Host ""

# Функция для выполнения команды через SSH с паролем
function SSH-Execute {
    param($Command)
    $passwordSecure = ConvertTo-SecureString $PASSWORD -AsPlainText -Force
    $cred = New-Object System.Management.Automation.PSCredential ($SERVER.Split('@')[0], $passwordSecure)
    
    # Используем plink (из PuTTY) для автоматического ввода пароля
    echo $PASSWORD | plink -ssh -batch -pw $PASSWORD $SERVER $Command
}

Write-Host "1. Обновление .env файла с CSRF настройками..." -ForegroundColor Yellow

$envContent = @"
# Django Settings
SECRET_KEY=django-insecure-production-key-change-me-in-production
DEBUG=False
ALLOWED_HOSTS=91.218.245.178,lootlink.duckdns.org

# CSRF Settings
CSRF_TRUSTED_ORIGINS=http://91.218.245.178,https://91.218.245.178,http://lootlink.duckdns.org,https://lootlink.duckdns.org

# Database Settings
DB_NAME=lootlink_db
DB_USER=lootlink_user
DB_PASSWORD=lootlink_password_secure_2024
DB_HOST=localhost
DB_PORT=5432

# Email Settings
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend

# AWS S3 Settings
USE_S3=False

# Redis Settings
USE_REDIS=True
REDIS_URL=redis://localhost:6379/0

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
"@

# Сохраняем временный файл
$envContent | Out-File -FilePath "temp_env" -Encoding UTF8 -NoNewline

Write-Host "2. Копирование файла на сервер..." -ForegroundColor Yellow
echo $PASSWORD | pscp -pw $PASSWORD temp_env ${SERVER}:${PROJECT_PATH}/.env

Write-Host "3. Перезапуск Gunicorn..." -ForegroundColor Yellow
echo $PASSWORD | plink -ssh -batch -pw $PASSWORD $SERVER "systemctl restart lootlink"

Write-Host "4. Проверка статуса..." -ForegroundColor Yellow
echo $PASSWORD | plink -ssh -batch -pw $PASSWORD $SERVER "systemctl status lootlink --no-pager | head -10"

# Удаляем временный файл
Remove-Item temp_env

Write-Host ""
Write-Host "=== ГОТОВО! ===" -ForegroundColor Green
Write-Host "Проверьте сайт: http://91.218.245.178" -ForegroundColor Cyan

