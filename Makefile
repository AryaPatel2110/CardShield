.PHONY: install preprocess train migrate infrastructure score produce api web up down test lint

install:
	python -m pip install -e ".[training,web,dev]"

preprocess:
	cardshield-preprocess

train:
	cardshield-train

migrate:
	cardshield-migrate

infrastructure:
	docker compose up -d kafka kafka-init cassandra migrate

score:
	cardshield-score

produce:
	cardshield-produce

api:
	cardshield-api

web:
	cd web && npm run dev

up:
	docker compose --profile demo up --build

down:
	docker compose --profile demo down

test:
	pytest

lint:
	ruff check src tests
	mypy
	cd web && npm run lint
