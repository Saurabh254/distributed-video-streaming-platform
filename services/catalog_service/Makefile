.PHONY: run test lint format

run:
	uv run uvicorn app.main:app --host 127.0.0.1 --port 8002 
test:
	uv run pytest -v

lint:
	uv run ruff check .

format:
	uv run ruff format .
