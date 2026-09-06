.PHONY: setup test build api web

setup:
	python3 -m venv backend/.venv
	backend/.venv/bin/pip install -r backend/requirements.txt
	cd frontend && npm install

test:
	backend/.venv/bin/pytest backend/tests -q

build:
	cd frontend && npm run build

api:
	cd backend && .venv/bin/uvicorn app.main:app --reload --env-file .env --port 8000

web:
	cd frontend && npm run dev
