@echo off
REM Быстрый запуск тестов
echo.
echo ========================================
echo   Запуск тестов LootLink
echo ========================================
echo.

REM Активация виртуального окружения
call venv\Scripts\activate.bat

REM Запуск тестов
python scripts\run_tests.py

pause

