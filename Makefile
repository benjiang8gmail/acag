.PHONY: setup dev api web build serve test test-backend test-web e2e migrate secret set-password recon scan backfill import import-folder members sides

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

backfill:         ## First run: ingest the last BACKFILL_MONTHS of Hansard for every enabled source
	$(UV) python -m app.cli backfill

scan:             ## Update: only new sitting days, changed documents and proofs still being corrected
	$(UV) python -m app.cli scan

import:           ## Manual import of one Hansard file (blocked sites): make import SRC=VIC-LA DATE=2026-09-24 FILE=/full/path.pdf [URL=https://...]
	$(UV) python -m app.cli import $(SRC) $(DATE) $(FILE) $(URL)

import-folder:    ## Manual import of a folder laid out as DIR/VIC-LA/2026-09-24.pdf: make import-folder DIR=/full/path
	$(UV) python -m app.cli import-folder $(DIR)

secret:           ## Print a new SESSION_SECRET for .env
	@$(UV) python -m app.cli secret

set-password:     ## Prompt for the password and print APP_PASSWORD_HASH for .env
	@$(UV) python -m app.cli hash-password

recon:            ## Phase 0: capture source fixtures politely (robots.txt, >=2 s per host); needs network access to the parliament and office hosts
	python3 -I scripts/recon_fetch.py --batch scripts/recon_batch.tsv --log docs/recon/recon-$$(date +%Y-%m-%d).jsonl

members:          ## Rebuild config/members/*.yaml from the parliaments' member lists (fetched politely)
	mkdir -p data/members-src
	python3 -I scripts/recon_fetch.py --batch scripts/members_batch.tsv --log docs/recon/members-$$(date +%Y-%m-%d).jsonl
	$(UV) python -I ../scripts/build_members.py ../data/members-src

sides:            ## Recompute party and speaker side for stored speeches after a members or governments change
	$(UV) python -m app.cli sides
