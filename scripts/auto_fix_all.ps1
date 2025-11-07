# =====================================================================
# АВТОМАТИЧЕСКАЯ ОЧИСТКА БД - PowerShell версия
# =====================================================================

Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host "  АВТОМАТИЧЕСКАЯ ОЧИСТКА БАЗЫ ДАННЫХ (Windows PowerShell)" -ForegroundColor Cyan
Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host ""

# Проверка manage.py
if (-not (Test-Path "manage.py")) {
    Write-Host "[ERROR] manage.py не найден!" -ForegroundColor Red
    Write-Host "Запустите скрипт из корневой директории проекта" -ForegroundColor Red
    exit 1
}

# Активация виртуального окружения
if (Test-Path "venv\Scripts\Activate.ps1") {
    Write-Host "[INFO] Активация виртуального окружения..." -ForegroundColor Yellow
    & "venv\Scripts\Activate.ps1"
}

Write-Host ""
Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host "ШАГ 1: ПРОВЕРКА БАЗЫ ДАННЫХ" -ForegroundColor Cyan
Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host ""

python scripts\check_database.py

Write-Host ""
Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host "ШАГ 2: ОЧИСТКА (АВТОМАТИЧЕСКИ)" -ForegroundColor Cyan
Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host ""

python scripts\auto_fix_all.py --auto

Write-Host ""
Write-Host "========================================================================" -ForegroundColor Green
Write-Host "ГОТОВО!" -ForegroundColor Green
Write-Host "========================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Следующие шаги:" -ForegroundColor Yellow
Write-Host "  1. Перезапустите Django сервер (Ctrl+C, затем python manage.py runserver)"
Write-Host "  2. Проверьте сайт: http://localhost:8000/requisites/"
Write-Host ""

Read-Host "Нажмите Enter для выхода"

