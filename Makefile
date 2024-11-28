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

api-restart:
	docker restart $(CONTAINER)

# Database commands
db-reset:
	docker cp sql/create_tables.sql $(DB_CONTAINER):/create_tables.sql
	$(PSQL) -c "DROP DATABASE IF EXISTS futures;"
	$(PSQL) -c "CREATE DATABASE futures;"
	$(PSQL) -d futures -f /create_tables.sql

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
