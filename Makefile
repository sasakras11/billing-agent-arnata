.PHONY: help install dev start stop restart logs test lint format clean docker-build docker-up docker-down

help:
	@echo "AI Billing Agent - Available Commands:"
	@echo "  make install       - Install dependencies"
	@echo "  make dev          - Run in development mode"
	@echo "  make start        - Start all services"
	@echo "  make stop         - Stop all services"
	@echo "  make restart      - Restart all services"
	@echo "  make logs         - View logs"
	@echo "  make test         - Run tests"
	@echo "  make lint         - Run linters"
	@echo "  make format       - Format code"
	@echo "  make clean        - Clean temporary files"
	@echo "  make docker-build - Build Docker images"
	@echo "  make docker-up    - Start Docker containers"
	@echo "  make docker-down  - Stop Docker containers"

install:
	pip install -r requirements.txt

dev:
	uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

start:
	@echo "Starting services..."
	uvicorn api.main:app --host 0.0.0.0 --port 8000 &
	celery -A tasks.celery_app worker --loglevel=info &
	celery -A tasks.celery_app beat --loglevel=info &

stop:
	@echo "Stopping services..."
	pkill -f "uvicorn api.main:app"
	pkill -f "celery"

restart: stop start

logs:
	tail -f logs/*.log

test:
	pytest tests/ -v --cov=. --cov-report=html

lint:
	ruff check .
	mypy .

format:
	black .
	ruff check --fix .

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.log" -delete
	rm -rf .pytest_cache
	rm -rf .coverage
	rm -rf htmlcov
	rm -rf dist
	rm -rf build
	rm -rf *.egg-info

docker-build:
	docker-compose build

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

migrate:
	alembic upgrade head

migrate-create:
	alembic revision --autogenerate -m "$(MSG)"

