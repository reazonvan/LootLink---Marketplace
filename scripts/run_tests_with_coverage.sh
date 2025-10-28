#!/bin/bash
# Скрипт для запуска тестов с coverage отчетом

echo "=========================================="
echo "  LootLink Test Suite with Coverage"
echo "=========================================="
echo ""

# Цвета для вывода
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Активация виртуального окружения (если нужно)
if [ -d "venv" ]; then
    echo -e "${YELLOW}Активация виртуального окружения...${NC}"
    source venv/bin/activate
fi

# Установка зависимостей для тестирования (если нужно)
echo -e "${YELLOW}Проверка зависимостей...${NC}"
pip install -q pytest pytest-django pytest-cov coverage factory-boy 2>/dev/null

# Очистка старых coverage данных
echo -e "${YELLOW}Очистка старых данных coverage...${NC}"
coverage erase
rm -rf htmlcov/
rm -f .coverage

# Запуск тестов с coverage
echo ""
echo -e "${GREEN}=== Запуск тестов ===${NC}"
echo ""

pytest \
    --verbose \
    --cov=. \
    --cov-report=html \
    --cov-report=term-missing \
    --cov-report=xml \
    --cov-config=.coveragerc \
    --tb=short \
    --maxfail=5 \
    -x

TEST_EXIT_CODE=$?

echo ""
echo "=========================================="

if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✓ Все тесты прошли успешно!${NC}"
else
    echo -e "${RED}✗ Некоторые тесты провалились${NC}"
    echo -e "${RED}  Exit code: $TEST_EXIT_CODE${NC}"
fi

echo "=========================================="
echo ""

# Генерация HTML отчета
if [ -f ".coverage" ]; then
    echo -e "${YELLOW}Генерация HTML отчета coverage...${NC}"
    coverage html
    
    echo ""
    echo -e "${GREEN}HTML отчет создан: htmlcov/index.html${NC}"
    echo ""
fi

# Вывод краткой статистики
echo "=========================================="
echo "  Coverage Summary"
echo "=========================================="
coverage report --skip-covered 2>/dev/null || coverage report

echo ""
echo "=========================================="
echo "  Детальный отчет:"
echo "  - HTML: htmlcov/index.html"
echo "  - XML: coverage.xml"
echo "=========================================="
echo ""

# Проверка минимального порога coverage
COVERAGE_PERCENT=$(coverage report | grep TOTAL | awk '{print $4}' | sed 's/%//')

if [ ! -z "$COVERAGE_PERCENT" ]; then
    if (( $(echo "$COVERAGE_PERCENT >= 70" | bc -l) )); then
        echo -e "${GREEN}✓ Coverage выше порога (${COVERAGE_PERCENT}% >= 70%)${NC}"
    else
        echo -e "${YELLOW}⚠ Coverage ниже порога (${COVERAGE_PERCENT}% < 70%)${NC}"
    fi
fi

echo ""

exit $TEST_EXIT_CODE

