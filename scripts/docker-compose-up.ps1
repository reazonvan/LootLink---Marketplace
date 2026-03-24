# Устанавливает PROJECT_ROOT для корректного bind mount на Docker Desktop (Windows).
# Запуск из корня репозитория: .\scripts\docker-compose-up.ps1
# Или: .\scripts\docker-compose-up.ps1 up -d

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
# Docker ожидает путь со слешами, как в POSIX
$env:PROJECT_ROOT = ($repoRoot -replace "\\", "/")

Write-Host "PROJECT_ROOT=$($env:PROJECT_ROOT)" -ForegroundColor Cyan

if (-not (Test-Path (Join-Path $repoRoot "manage.py"))) {
    Write-Error "manage.py не найден в $repoRoot"
    exit 1
}

Set-Location $repoRoot
docker compose @args
