.PHONY: setup test build api web benchmark

setup:
	python3 -m venv backend/.venv
	backend/.venv/bin/pip install -r backend/requirements.txt
	cd frontend && npm install

test:
	backend/.venv/bin/pytest backend/tests -q
	cd frontend && npm test

benchmark:
	backend/.venv/bin/python backend/scripts/benchmark.py

build:
	cd frontend && npm run build

api:
	cd backend && .venv/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

web:
	cd frontend && npm run dev
