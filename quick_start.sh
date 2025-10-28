#!/bin/bash
# ===================================
# LootLink Quick Start (Linux/Mac)
# ===================================

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo ""
echo "==================================="
echo "  LootLink Quick Start"
echo "==================================="
echo ""

# Проверка виртуального окружения
if [ ! -d "venv" ]; then
    echo -e "${BLUE}[1/6]${NC} Creating virtual environment..."
    python3 -m venv venv
    echo -e "${GREEN}[OK]${NC} Virtual environment created"
else
    echo -e "${GREEN}[OK]${NC} Virtual environment exists"
fi

echo ""
echo -e "${BLUE}[2/6]${NC} Activating virtual environment..."
source venv/bin/activate

echo ""
echo -e "${BLUE}[3/6]${NC} Installing dependencies..."
pip install -r requirements.txt --quiet

echo ""
echo -e "${BLUE}[4/6]${NC} Applying migrations..."
python manage.py migrate

echo ""
echo -e "${BLUE}[5/6]${NC} Collecting static files..."
python manage.py collectstatic --noinput

echo ""
echo -e "${BLUE}[6/6]${NC} Starting development server..."
echo ""
echo "==================================="
echo "  Server starting..."
echo "  URL: http://127.0.0.1:8000"
echo "  Admin: http://127.0.0.1:8000/admin"
echo "==================================="
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

python manage.py runserver

