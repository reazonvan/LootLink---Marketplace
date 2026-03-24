.PHONY: help install test lint format clean run migrate shell docker-up-win

help:
	@echo "LootLink Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make install       Install all dependencies"
	@echo "  make setup         Full project setup (install + migrate)"
	@echo ""
	@echo "Development:"
	@echo "  make run           Run Django development server"
	@echo "  make shell         Open Django shell"
	@echo "  make migrate       Run database migrations"
	@echo "  make makemigrations Create new migrations"
	@echo ""
	@echo "Testing:"
	@echo "  make test          Run all tests"
	@echo "  make test-fast     Run tests without coverage"
	@echo "  make coverage      Generate coverage report"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint          Run all linters"
	@echo "  make format        Format code with black and isort"
	@echo "  make check         Run Django checks"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-up     Start Docker containers"
	@echo "  make docker-up-win Windows: подставляет PROJECT_ROOT для bind mount"
	@echo "  make docker-down   Stop Docker containers"
	@echo "  make docker-logs   Show Docker logs"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean         Remove temporary files"
	@echo "  make clean-all     Remove all generated files"

install:
	pip install --upgrade pip
	pip install -r requirements/development.txt

setup: install
	python manage.py migrate
	python manage.py collectstatic --noinput

run:
	python manage.py runserver

shell:
	python manage.py shell

migrate:
	python manage.py migrate

makemigrations:
	python manage.py makemigrations

test:
	pytest -v

test-fast:
	pytest -v --no-cov

coverage:
	pytest --cov=. --cov-report=html
	@echo "Coverage report generated in htmlcov/index.html"

lint:
	flake8 .
	pylint **/*.py
	mypy .
	bandit -r . -c pyproject.toml

format:
	black .
	isort .

check:
	python manage.py check

docker-up:
	docker-compose up -d

docker-up-win:
	powershell -NoProfile -ExecutionPolicy Bypass -File scripts/docker-compose-up.ps1 up -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.coverage" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +

clean-all: clean
	rm -rf venv/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf staticfiles/
