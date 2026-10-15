# NeuralShelf backend

FastAPI + PostgreSQL/pgvector + Ollama. Users upload PDFs, a worker indexes
them, and users search and chat with their documents, with citations.

## Run locally

Prerequisites: Docker, `make`, and [Ollama](https://ollama.com) running on the
host with the models pulled:

```bash
ollama pull nomic-embed-text
ollama pull qwen3.5:2b-q4_K_M
```

First run (from the repository root):

```bash
cp backend/.env.example backend/.env   # then set JWT_SECRET_KEY
make setup                             # build, start db, migrate, seed, start api + worker
```

- API docs: http://localhost:8000/docs
- Seeded logins: `admin@neuralshelf.local / Admin!12345` (admin), `demo@neuralshelf.local / Demo!12345`

## Commands

Run `make` to list them all. Database commands run in a temporary api
container (`docker compose run --rm`), so no extra service is needed.

| Make | Same thing without make | What it does |
|---|---|---|
| `make up` | `docker compose up -d db && … migrate && docker compose up -d api worker` | Start everything, applying pending migrations first |
| `make down` | `docker compose down` | Stop everything (data is kept) |
| `make migrate` | `python -m neuralshelf.cli migrate` | Apply all pending migrations |
| `make migrate-status` | `python -m neuralshelf.cli migrate:status` | List applied / pending migrations |
| `make rollback ARGS="--steps 2"` | `python -m neuralshelf.cli migrate:rollback --steps 2` | Undo the latest migration(s) |
| `make fresh` | `python -m neuralshelf.cli migrate:fresh` | **Drop all data and uploads**, re-run every migration (asks first) |
| `make fresh-seed` | `python -m neuralshelf.cli migrate:fresh --seed` | Same, then seed |
| `make seed` | `python -m neuralshelf.cli db:seed [--only users\|documents]` | Insert dev data (safe to run twice) |
| `make make-migration m="add x"` | `python -m neuralshelf.cli make:migration "add x"` | Autogenerate a migration from model changes; review it before applying |
| `make admin email=a@b.c` | `python -m neuralshelf.cli promote-admin a@b.c` | Grant admin access (`demote-admin` to revoke) |
| `make restart-worker` | `docker compose restart worker` | Reload worker code (finishes its current job first) |
| `make logs` / `make db-shell` | | Follow logs / open psql |

The `python -m neuralshelf.cli …` forms work from `backend/` with the local
venv (`.venv/bin/python -m neuralshelf.cli …`) or inside a container.

Safety: `migrate:fresh`, `migrate:rollback` and `db:seed` refuse to run when
`APP_ENV=production`. Concurrent `migrate` runs are serialized by a PostgreSQL
advisory lock, so two deploys migrating at once is safe.

### Production deploys

Run `python -m neuralshelf.cli migrate` once as a release step (e.g. a CI/CD
job or `docker run --rm <image> python -m neuralshelf.cli migrate`), then roll
out the api and worker containers. Never use `fresh` or `seed` there.

## Services

| Service | Role |
|---|---|
| `db` | PostgreSQL 17 + pgvector |
| `api` | HTTP API (`neuralshelf.main:app`) |
| `worker` | Processes the ingestion job queue (`neuralshelf.workers.ingestion_worker`); scale with `--scale worker=N` |

## Development without Docker for the app

```bash
cd backend
python -m venv .venv && .venv/bin/pip install -e ".[dev]"
docker compose up -d db
.venv/bin/python -m neuralshelf.cli migrate
.venv/bin/python -m neuralshelf.cli db:seed
.venv/bin/uvicorn neuralshelf.main:app --reload
.venv/bin/python -m neuralshelf.workers.ingestion_worker   # second terminal
```

## Tests

```bash
.venv/bin/pytest                 # unit + integration (needs the db service; uses a separate neuralshelf_test database)
.venv/bin/pytest -m evaluation   # quality checks against the real Ollama models
.venv/bin/ruff check src tests --exclude src/neuralshelf/db/migrations
```

CI (`.github/workflows/backend-ci.yml`) runs lint, migrations from an empty
database, `alembic check`, the test suite and a production image build.

## Key design points

- **Ingestion job queue in PostgreSQL** (`ingestion_jobs`): the job is created in
  the same transaction as the document, claimed with `FOR UPDATE SKIP LOCKED`,
  protected by a renewable lease (crashed workers' jobs are resumed), fenced
  completion, retries with exponential backoff, and a max-attempts limit.
- **Streaming chat** over Server-Sent Events: `POST /conversations/{id}/messages/stream`
  emits `start` (citations), `token`..., then `done` or `error`. Nothing is saved
  unless the answer completes.
- **Vector search** uses an HNSW index (cosine) with pgvector's iterative scan so
  per-user filtering still returns full results.
- **Every query is scoped to the authenticated user**; other users' resources return 404.
- **Responses** use one envelope: `{success, code, message, data: [...]}`; list
  endpoints add `pagination`. Every response carries `X-Request-ID`, which also
  appears in the logs (`LOG_FORMAT=json` in production).
