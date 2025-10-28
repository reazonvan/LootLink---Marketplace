@echo off
REM Проверка качества кода
echo.
echo ========================================
echo   Проверка качества кода LootLink
echo ========================================
echo.

REM Активация виртуального окружения
call venv\Scripts\activate.bat

REM Запуск проверки
python scripts\check_code_quality.py

pause

