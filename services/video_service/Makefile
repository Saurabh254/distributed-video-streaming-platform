PORT ?= 8001
HOST ?= 127.0.0.1

.PHONY: run format lint test worker dispatcher

run:
	uv run uvicorn app.main:app --port $(PORT) --host $(HOST) --reload

worker:
	uv run dramatiq app.workers.actors --processes 2 --threads 4

dispatcher:
	uv run python -m app.workers.dispatcher

format:
	uv run ruff format .
	uv run ruff check --fix .

lint:
	uv run ruff check .
	uv run ruff format --check .

test:
	uv run pytest
