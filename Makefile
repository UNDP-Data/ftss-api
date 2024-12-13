# Container configuration
CONTAINER = ftss-api-web-1
DB_CONTAINER = ftss-api-db-1
DC = docker compose
PSQL = docker exec -it $(DB_CONTAINER) psql -U postgres
DOCKER_COMPOSE_FILE = docker-compose.yaml

# Main commands
.PHONY: up down build start restart logs install format lint test db-*

# Docker commands
up:
	$(DC) up -d --remove-orphans --force-recreate web
# x
down:
	$(DC) down

build:
	$(DC) build --no-cache

start: build up

restart: down start

logs:
	docker logs -f $(CONTAINER)

venv:
	source venv/bin/activate

# API service commands
api-stop:
	docker stop $(CONTAINER)

api-pause:
	docker pause $(CONTAINER)

api-unpause:
	docker unpause $(CONTAINER)
# x
api-restart:
	docker restart $(CONTAINER)
# z
# Database commands
db-reset:
	docker cp sql/create_tables.sql $(DB_CONTAINER):/create_tables.sql
	docker cp sql/create_test_user.sql $(DB_CONTAINER):/create_test_user.sql
	$(PSQL) -d template1 -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'postgres' AND pid <> pg_backend_pid();"
	$(PSQL) -d template1 -c "DROP DATABASE IF EXISTS postgres;"
	$(PSQL) -d template1 -c "CREATE DATABASE postgres;"
	$(PSQL) -d postgres -f /create_tables.sql
	$(PSQL) -d postgres -f /create_test_user.sql

db: api-stop db-reset up

# Development commands
install:
	pip install --upgrade pip && pip install -r requirements_dev.txt

format:
	isort . --profile black --multi-line 3 && black .

lint:
	pylint main.py src/

test:
	python -m pytest tests/

test-docker:
	docker exec -it $(CONTAINER) sh -c "pip install pytest && PYTHONPATH=/app pytest /app/tests/"

test-docker-watch:
	docker exec -it $(CONTAINER) sh -c "pip install pytest pytest-watch && PYTHONPATH=/app pytest --watch /app/tests/"