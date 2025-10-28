@echo off
echo Starting LootLink server...
echo.

REM Activate virtual environment if exists
if exist venv\Scripts\activate.bat (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
)

REM Create migrations
echo Creating migrations...
python manage.py makemigrations accounts
python manage.py makemigrations listings
python manage.py migrate

REM Start server
echo Starting Django server...
python manage.py runserver 8000
