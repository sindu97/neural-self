# NeuralShelf developer commands. Run `make` or `make help` to list them.
#
# Database commands run inside a temporary api container
# (`docker compose run --rm`), so they use the same environment as the app.
# Pass extra arguments with ARGS, e.g. `make rollback ARGS="--steps 2"`.

COMPOSE := docker compose
CLI := $(COMPOSE) run --rm --no-deps api python -m neuralshelf.cli

.DEFAULT_GOAL := help
.PHONY: help setup up down restart-worker logs ps \
        migrate migrate-status rollback fresh fresh-seed make-migration seed admin \
        test test-eval lint db-shell

help: ## List commands
	@grep -hE '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F ':.*## ' '{printf "  make %-16s %s\n", $$1, $$2}'

# ---- stack ---------------------------------------------------------------

setup: ## First run: build, start db, migrate, seed, start api + worker
	$(COMPOSE) build
	$(COMPOSE) up -d db
	$(MAKE) migrate seed
	$(COMPOSE) up -d api worker

up: ## Start everything and apply pending migrations
	$(COMPOSE) up -d db
	$(MAKE) migrate
	$(COMPOSE) up -d api worker

down: ## Stop everything (data is kept)
	$(COMPOSE) down

restart-worker: ## Restart the worker after code changes (finishes its current job first)
	$(COMPOSE) restart worker

logs: ## Follow api + worker logs
	$(COMPOSE) logs -f api worker

ps: ## Show service status
	$(COMPOSE) ps

# ---- database ------------------------------------------------------------

migrate: ## Apply all pending migrations
	$(CLI) migrate

migrate-status: ## Show applied and pending migrations
	$(CLI) migrate:status

rollback: ## Undo the latest migration (ARGS="--steps N" for more)
	$(CLI) migrate:rollback $(ARGS)

fresh: ## DROP ALL DATA and re-run every migration (asks for confirmation)
	$(COMPOSE) run --rm --no-deps -it api python -m neuralshelf.cli migrate:fresh $(ARGS)

fresh-seed: ## DROP ALL DATA, re-run every migration, then seed (asks for confirmation)
	$(COMPOSE) run --rm --no-deps -it api python -m neuralshelf.cli migrate:fresh --seed $(ARGS)

make-migration: ## Autogenerate a migration: make make-migration m="add x to y"
	@test -n "$(m)" || (echo 'Usage: make make-migration m="describe the change"' && exit 1)
	$(CLI) make:migration "$(m)"

seed: ## Insert development seed data (admin, demo user, sample document)
	$(CLI) db:seed $(ARGS)

admin: ## Make a user an administrator: make admin email=you@example.com
	@test -n "$(email)" || (echo 'Usage: make admin email=you@example.com' && exit 1)
	$(CLI) promote-admin "$(email)"

db-shell: ## Open psql on the development database
	$(COMPOSE) exec db psql -U neuralshelf -d neuralshelf

# ---- quality -------------------------------------------------------------

test: ## Unit + integration tests (local venv, needs the db service)
	cd backend && .venv/bin/pytest

test-eval: ## Quality tests against the real Ollama models
	cd backend && .venv/bin/pytest -m evaluation

lint: ## Lint
	cd backend && .venv/bin/ruff check src tests --exclude src/neuralshelf/db/migrations
