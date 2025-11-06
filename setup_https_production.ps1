# ==========================================
# Setup HTTPS on Production Server
# ==========================================

$server = "root@91.218.245.178"

Write-Host "🔐 Настройка HTTPS на production сервере..." -ForegroundColor Cyan
Write-Host ""

# Step 1: Upload scripts
Write-Host "📤 Step 1: Загрузка скриптов на сервер..." -ForegroundColor Yellow
scp scripts/setup_https.sh ${server}:/tmp/
scp scripts/enable_django_https.sh ${server}:/tmp/
Write-Host "✅ Скрипты загружены" -ForegroundColor Green
Write-Host ""

# Step 2: Make scripts executable and run HTTPS setup
Write-Host "🔧 Step 2: Установка SSL сертификата..." -ForegroundColor Yellow
ssh $server @"
chmod +x /tmp/setup_https.sh
chmod +x /tmp/enable_django_https.sh
/tmp/setup_https.sh
"@

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Ошибка при настройке SSL" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Step 3: Enable Django HTTPS settings
Write-Host "⚙️  Step 3: Обновление Django настроек..." -ForegroundColor Yellow
ssh $server "/tmp/enable_django_https.sh"

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Ошибка при обновлении Django настроек" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Green
Write-Host "✅ HTTPS успешно настроен!" -ForegroundColor Green
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Green
Write-Host ""
Write-Host "🌐 Сайт теперь доступен по адресу:" -ForegroundColor Cyan
Write-Host "   https://91.218.245.178" -ForegroundColor White
Write-Host ""
Write-Host "⚠️  ВАЖНО:" -ForegroundColor Yellow
Write-Host "   Используется самоподписанный сертификат" -ForegroundColor White
Write-Host "   Браузер покажет предупреждение о безопасности" -ForegroundColor White
Write-Host "   Это нормально для IP адреса без доменного имени" -ForegroundColor White
Write-Host ""
Write-Host "💡 Для устранения предупреждения:" -ForegroundColor Yellow
Write-Host "   1. Купите доменное имя (например, lootlink.ru)" -ForegroundColor White
Write-Host "   2. Настройте DNS A-запись на 91.218.245.178" -ForegroundColor White
Write-Host "   3. Установите Let's Encrypt сертификат" -ForegroundColor White
Write-Host ""
Write-Host "🧪 Проверка сайта..." -ForegroundColor Cyan

# Test HTTPS connection
try {
    Write-Host "   Тестирование HTTPS соединения..."
    $response = Invoke-WebRequest -Uri "https://91.218.245.178" -SkipCertificateCheck -TimeoutSec 10 -ErrorAction Stop
    if ($response.StatusCode -eq 200) {
        Write-Host "   ✅ HTTPS работает!" -ForegroundColor Green
    }
} catch {
    Write-Host "   ⚠️  Не удалось проверить HTTPS (возможно, нужно подождать)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "✨ Готово! Откройте https://91.218.245.178 в браузере" -ForegroundColor Green
Write-Host ""

