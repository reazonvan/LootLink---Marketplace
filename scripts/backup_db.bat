@echo off
REM ===================================================================
REM PostgreSQL Database Backup Script for LootLink (Windows)
REM Автоматическое резервное копирование БД с ротацией старых бекапов
REM ===================================================================

setlocal enabledelayedexpansion

REM Конфигурация
set TIMESTAMP=%DATE:~-4%%DATE:~3,2%%DATE:~0,2%_%TIME:~0,2%%TIME:~3,2%%TIME:~6,2%
set TIMESTAMP=%TIMESTAMP: =0%
set BACKUP_DIR=C:\backups\lootlink
set DB_NAME=lootlink_db
set DB_USER=postgres
set DB_HOST=localhost
set DB_PORT=5432
set RETENTION_DAYS=30

echo ===================================
echo LootLink Database Backup
echo ===================================
echo Timestamp: %TIMESTAMP%
echo Database: %DB_NAME%
echo Backup directory: %BACKUP_DIR%
echo.

REM Создаём директорию для бекапов
if not exist "%BACKUP_DIR%" (
    echo Creating backup directory...
    mkdir "%BACKUP_DIR%"
)

REM Имя файла бекапа
set BACKUP_FILE=%BACKUP_DIR%\lootlink_backup_%TIMESTAMP%.sql

REM Создаём бекап
echo Creating backup...
pg_dump -U %DB_USER% -h %DB_HOST% -p %DB_PORT% %DB_NAME% > "%BACKUP_FILE%"

if %ERRORLEVEL% EQU 0 (
    echo [OK] Backup created: %BACKUP_FILE%
    
    REM Показываем размер файла
    for %%A in ("%BACKUP_FILE%") do (
        set SIZE=%%~zA
        set /A SIZE_MB=!SIZE! / 1048576
        echo Backup size: !SIZE_MB! MB
    )
) else (
    echo [ERROR] Failed to create backup
    exit /b 1
)

REM Удаляем старые бекапы (старше RETENTION_DAYS дней)
echo.
echo Cleaning old backups (older than %RETENTION_DAYS% days)...
forfiles /P "%BACKUP_DIR%" /M lootlink_backup_*.sql /D -%RETENTION_DAYS% /C "cmd /c del @path" 2>nul

if %ERRORLEVEL% EQU 0 (
    echo [OK] Old backups deleted
) else (
    echo [OK] No old backups to delete
)

REM Показываем список всех бекапов
echo.
echo ===================================
echo All backups:
echo ===================================
dir /B /O-D "%BACKUP_DIR%\lootlink_backup_*.sql" 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo No backups found
)

echo.
echo ===================================
echo Backup completed successfully!
echo ===================================

endlocal
exit /b 0
