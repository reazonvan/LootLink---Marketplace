@echo off
REM ===================================
REM LootLink Quick Start (Windows)
REM ===================================

echo.
echo ===================================
echo   LootLink Quick Start
echo ===================================
echo.

REM Проверка виртуального окружения
if not exist "venv\" (
    echo [1/6] Creating virtual environment...
    python -m venv venv
    echo [OK] Virtual environment created
) else (
    echo [OK] Virtual environment exists
)

echo.
echo [2/6] Activating virtual environment...
call venv\Scripts\activate

echo.
echo [3/6] Installing dependencies...
pip install -r requirements.txt --quiet

echo.
echo [4/6] Applying migrations...
python manage.py migrate

echo.
echo [5/6] Collecting static files...
python manage.py collectstatic --noinput

echo.
echo [6/6] Starting development server...
echo.
echo ===================================
echo   Server starting...
echo   URL: http://127.0.0.1:8000
echo   Admin: http://127.0.0.1:8000/admin
echo ===================================
echo.
echo Press Ctrl+C to stop the server
echo.

python manage.py runserver

pause

