# Faro – common commands
# Usage: make [target]

.PHONY: up down logs dev-backend dev-frontend env-setup test test-coverage

# Docker: start backend + Neo4j
up:
	docker compose up -d

# Docker: stop and remove containers
down:
	docker compose down

# Docker: follow logs
logs:
	docker compose logs -f

# Local dev: run backend (uses backend/.venv if present, .env required)
dev-backend:
	cd backend && (test -d .venv && exec .venv/bin/python -m uvicorn app.main:app --reload --port 8000 || exec python -m uvicorn app.main:app --reload --port 8000)

# Local dev: run frontend (Bun)
dev-frontend:
	cd frontend && bun run dev

# Run backend tests
test:
	cd backend && PYTHONPATH=. python -m pytest tests -v

# Run tests with coverage report
test-coverage:
	cd backend && PYTHONPATH=. python -m pytest tests -v --cov=app --cov-report=term-missing

# Copy backend .env.example to .env if missing
env-setup:
	@if [ ! -f backend/.env ]; then cp backend/.env.example backend/.env && echo "Created backend/.env – set ETHERSCAN_API_KEY"; else echo "backend/.env already exists"; fi
