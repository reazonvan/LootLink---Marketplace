# PowerShell скрипт для деплоя на сервер через SSH
# Использование: .\deploy_to_server.ps1

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  ДЕПЛОЙ НА ПРОДАКШН СЕРВЕР 91.218.245.178" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

$server = "root@91.218.245.178"
$commands = @"
cd /opt/lootlink
git pull origin main
chmod +x FIX_SERVER_NOW.sh
./FIX_SERVER_NOW.sh
"@

Write-Host "Подключение к серверу $server..." -ForegroundColor Yellow
Write-Host ""

# Проверяем наличие ssh
$sshPath = Get-Command ssh -ErrorAction SilentlyContinue

if (-not $sshPath) {
    Write-Host "ОШИБКА: SSH не найден в системе!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Установите OpenSSH:" -ForegroundColor Yellow
    Write-Host "Settings -> Apps -> Optional Features -> OpenSSH Client" -ForegroundColor White
    Write-Host ""
    Write-Host "Или выполните вручную:" -ForegroundColor Yellow
    Write-Host "ssh $server" -ForegroundColor White
    Write-Host "Затем:" -ForegroundColor Yellow
    Write-Host $commands -ForegroundColor White
    exit 1
}

Write-Host "Выполнение команд на сервере..." -ForegroundColor Yellow
Write-Host ""

# Сохраняем команды во временный файл
$tempFile = [System.IO.Path]::GetTempFileName()
$commands | Out-File -FilePath $tempFile -Encoding UTF8

try {
    # Выполняем команды на сервере
    ssh $server "bash -s" < $tempFile
    
    Write-Host ""
    Write-Host "================================================" -ForegroundColor Green
    Write-Host "  ДЕПЛОЙ ЗАВЕРШЕН!" -ForegroundColor Green
    Write-Host "================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Теперь откройте в браузере (режим инкогнито):" -ForegroundColor Yellow
    Write-Host "http://91.218.245.178" -ForegroundColor Cyan
    Write-Host ""
}
catch {
    Write-Host ""
    Write-Host "ОШИБКА при выполнении команд:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Write-Host ""
    Write-Host "Попробуйте выполнить вручную:" -ForegroundColor Yellow
    Write-Host "ssh $server" -ForegroundColor White
    Write-Host $commands -ForegroundColor White
}
finally {
    # Удаляем временный файл
    Remove-Item -Path $tempFile -Force -ErrorAction SilentlyContinue
}

