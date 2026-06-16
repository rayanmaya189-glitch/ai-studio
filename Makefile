.PHONY: help up down backend frontend backend-build backend-prod frontend-build frontend-prod install-backend install-frontend test fmt

help:
	@echo "ADS dev/prod shortcuts:"
	@echo "  make up                   start postgres + qdrant (docker compose)"
	@echo "  make down                 stop backing services"
	@echo "  make install-backend      create venv + install backend deps"
	@echo "  make install-frontend     npm install in frontend/"
	@echo "  make backend              run FastAPI dev server (port 8754)"
	@echo "  make frontend             run Next.js dev server (port 3000)"
	@echo "  make backend-build       backend production build step (bytecode compile)"
	@echo "  make backend-prod         run FastAPI prod server (no --reload)"
	@echo "  make frontend-build      build Next.js production bundle"
	@echo "  make frontend-prod        run Next.js production server"
	@echo "  make test                 run backend pytest suite"
	@echo "  make fmt                  ruff format + check backend"

up:
	docker compose up -d postgres qdrant

down:
	docker compose down

install-backend:
	cd backend && python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt

install-frontend:
	cd frontend && npm install

backend:
	cd backend && . .venv/bin/activate && uvicorn app.main:app --reload --port 8754

backend-build:
	cd backend && . .venv/bin/activate && python -m compileall -q app

backend-prod:
	cd backend && . .venv/bin/activate && uvicorn app.main:app --port 8754

frontend:
	cd frontend && npm run dev

frontend-build:
	cd frontend && npm run build

frontend-prod:
	cd frontend && npm run start

test:
	cd backend && . .venv/bin/activate && pytest -q

fmt:
	cd backend && . .venv/bin/activate && ruff format app tests && ruff check --fix app tests
