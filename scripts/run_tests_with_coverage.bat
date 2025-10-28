@echo off
REM Скрипт для запуска тестов с coverage отчетом (Windows)

echo ==========================================
echo   LootLink Test Suite with Coverage
echo ==========================================
echo.

REM Активация виртуального окружения
if exist venv\Scripts\activate.bat (
    echo Активация виртуального окружения...
    call venv\Scripts\activate.bat
) else (
    echo WARNING: Виртуальное окружение не найдено
)

REM Установка зависимостей для тестирования
echo Проверка зависимостей...
pip install -q pytest pytest-django pytest-cov coverage factory-boy 2>nul

REM Очистка старых coverage данных
echo Очистка старых данных coverage...
if exist htmlcov rmdir /s /q htmlcov
if exist .coverage del .coverage
if exist coverage.xml del coverage.xml

REM Запуск тестов с coverage
echo.
echo === Запуск тестов ===
echo.

pytest ^
    --verbose ^
    --cov=. ^
    --cov-report=html ^
    --cov-report=term-missing ^
    --cov-report=xml ^
    --cov-config=.coveragerc ^
    --tb=short ^
    --maxfail=5 ^
    -x

set TEST_EXIT_CODE=%ERRORLEVEL%

echo.
echo ==========================================

if %TEST_EXIT_CODE% EQU 0 (
    echo [OK] Все тесты прошли успешно!
) else (
    echo [ERROR] Некоторые тесты провалились
    echo   Exit code: %TEST_EXIT_CODE%
)

echo ==========================================
echo.

REM Генерация HTML отчета
if exist .coverage (
    echo Генерация HTML отчета coverage...
    coverage html
    
    echo.
    echo HTML отчет создан: htmlcov\index.html
    echo.
)

REM Вывод краткой статистики
echo ==========================================
echo   Coverage Summary
echo ==========================================
coverage report --skip-covered 2>nul || coverage report

echo.
echo ==========================================
echo   Детальный отчет:
echo   - HTML: htmlcov\index.html
echo   - XML: coverage.xml
echo ==========================================
echo.

REM Открыть HTML отчет в браузере (опционально)
REM start htmlcov\index.html

pause
exit /b %TEST_EXIT_CODE%

