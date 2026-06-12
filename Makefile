.PHONY: up down up-data test lint

up:
	docker compose up -d

up-data:
	docker compose -f docker-compose.yml -f docker-compose.data.yml up -d

down:
	docker compose down

test:
	pytest tests/unit -m "not gpu and not integration"

lint:
	ruff check .
