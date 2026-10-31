.PHONY: setup dev api web build serve test test-backend test-web e2e migrate secret set-password recon

UV := cd backend && UV_SYSTEM_CERTS=1 uv run

setup:            ## Install backend and web dependencies, create .env
	cd backend && uv sync
	cd web && npm ci
	@test -f .env || (cp .env.example .env && echo "Created .env — now run: make secret, make set-password")

migrate:
	$(UV) alembic upgrade head

dev:              ## API on :8000 and web on :5173 (proxying /api)
	$(MAKE) -j2 api web

api:
	$(UV) uvicorn app.main:app --reload --port 8000

web:
	cd web && npm run dev

build:
	cd web && npm run build

serve: build      ## One process serving the built web app and the API on :8000
	$(UV) uvicorn app.main:app --host 0.0.0.0 --port 8000

test: test-backend test-web

test-backend:
	$(UV) pytest -q

test-web:
	cd web && npm run typecheck && npm test

e2e:              ## Playwright journeys + axe; needs `make serve` running and E2E_PASSWORD set
	cd web && npx playwright test

secret:           ## Print a new SESSION_SECRET for .env
	@$(UV) python -m app.cli secret

set-password:     ## Prompt for the password and print APP_PASSWORD_HASH for .env
	@$(UV) python -m app.cli hash-password

recon:            ## Phase 0: capture source fixtures politely (robots.txt, >=2 s per host); needs network access to the parliament and office hosts
	python3 -I scripts/recon_fetch.py --batch scripts/recon_batch.tsv --log docs/recon/recon-$$(date +%Y-%m-%d).jsonl
