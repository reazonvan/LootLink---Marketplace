# Скрипт для автоматического развертывания LootLink на VPS

$SERVER_IP = "91.218.245.178"
$SERVER_USER = "root"
$SERVER_PASSWORD = "BWJ_1anRP0"
$PROJECT_PATH = "C:\Users\ivanp\Desktop\LootLink"

Write-Host "🚀 Начинаем развертывание LootLink на VPS..." -ForegroundColor Green
Write-Host ""

# Проверка наличия ssh
$sshExists = Get-Command ssh -ErrorAction SilentlyContinue
if (-not $sshExists) {
    Write-Host "❌ SSH клиент не найден. Установите OpenSSH." -ForegroundColor Red
    exit 1
}

Write-Host "[1/7] 📁 Создание директории на сервере..." -ForegroundColor Cyan
$createDir = @"
mkdir -p /opt/lootlink
echo 'OK'
"@
$createDir | ssh ${SERVER_USER}@${SERVER_IP} "bash -s"

Write-Host "[2/7] 📤 Загрузка основных файлов проекта..." -ForegroundColor Cyan
scp -r "$PROJECT_PATH\accounts" "${SERVER_USER}@${SERVER_IP}:/opt/lootlink/"
scp -r "$PROJECT_PATH\chat" "${SERVER_USER}@${SERVER_IP}:/opt/lootlink/"
scp -r "$PROJECT_PATH\config" "${SERVER_USER}@${SERVER_IP}:/opt/lootlink/"
scp -r "$PROJECT_PATH\core" "${SERVER_USER}@${SERVER_IP}:/opt/lootlink/"
scp -r "$PROJECT_PATH\listings" "${SERVER_USER}@${SERVER_IP}:/opt/lootlink/"
scp -r "$PROJECT_PATH\transactions" "${SERVER_USER}@${SERVER_IP}:/opt/lootlink/"
scp -r "$PROJECT_PATH\static" "${SERVER_USER}@${SERVER_IP}:/opt/lootlink/"
scp -r "$PROJECT_PATH\templates" "${SERVER_USER}@${SERVER_IP}:/opt/lootlink/"
scp -r "$PROJECT_PATH\scripts" "${SERVER_USER}@${SERVER_IP}:/opt/lootlink/"

Write-Host "[3/7] 📄 Загрузка конфигурационных файлов..." -ForegroundColor Cyan
scp "$PROJECT_PATH\manage.py" "${SERVER_USER}@${SERVER_IP}:/opt/lootlink/"
scp "$PROJECT_PATH\requirements.txt" "${SERVER_USER}@${SERVER_IP}:/opt/lootlink/"

Write-Host "[4/7] 📦 Загрузка экспортированных данных..." -ForegroundColor Cyan
scp "$PROJECT_PATH\exports\lootlink_data_backup.json" "${SERVER_USER}@${SERVER_IP}:/opt/lootlink/"
scp "$PROJECT_PATH\exports\lootlink_media_backup.zip" "${SERVER_USER}@${SERVER_IP}:/opt/lootlink/"

Write-Host "[5/7] 🔧 Запуск установки на сервере (это займет 5-10 минут)..." -ForegroundColor Cyan
$deployScript = @"
cd /opt/lootlink
chmod +x scripts/deploy_to_vps.sh
export DEBIAN_FRONTEND=noninteractive
bash scripts/deploy_to_vps.sh
"@
$deployScript | ssh ${SERVER_USER}@${SERVER_IP} "bash -s"

Write-Host "[6/7] 📥 Импорт данных..." -ForegroundColor Cyan
$importData = @"
cd /opt/lootlink
source venv/bin/activate
python manage.py loaddata lootlink_data_backup.json
"@
$importData | ssh ${SERVER_USER}@${SERVER_IP} "bash -s"

Write-Host "[7/7] 🖼️ Распаковка медиа файлов..." -ForegroundColor Cyan
$extractMedia = @"
cd /opt/lootlink
unzip -o lootlink_media_backup.zip
chown -R www-data:www-data media/
"@
$extractMedia | ssh ${SERVER_USER}@${SERVER_IP} "bash -s"

Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║          ✅ РАЗВЕРТЫВАНИЕ ЗАВЕРШЕНО УСПЕШНО!              ║" -ForegroundColor Green
Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""
Write-Host "🌐 Ваш сайт доступен: http://91.218.245.178" -ForegroundColor Yellow
Write-Host "📊 Админ-панель: http://91.218.245.178/admin/" -ForegroundColor Yellow
Write-Host ""

