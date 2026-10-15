# NeuralShelf backend

FastAPI + PostgreSQL/pgvector + Ollama. Users upload PDFs, a worker indexes
them, and users search and chat with their documents, with citations.

## Run locally

Prerequisites: Docker, and [Ollama](https://ollama.com) running on the host with
the models pulled:

```bash
ollama pull nomic-embed-text
ollama pull qwen3.5:2b-q4_K_M
```

```bash
cp backend/.env.example backend/.env   # then set JWT_SECRET_KEY
docker compose up -d --build           # db -> migrate -> api + worker
```

- API docs: http://localhost:8000/docs
- Health: http://localhost:8000/api/v1/health/ready
- Worker logs: `docker compose logs -f worker`
- After changing worker code: `docker compose restart worker` (the API reloads by itself)
- Make someone an admin: `docker compose exec api python -m neuralshelf.cli promote-admin you@example.com`

## Services

| Service | Role |
|---|---|
| `db` | PostgreSQL 17 + pgvector |
| `migrate` | Runs `alembic upgrade head`, then exits |
| `api` | HTTP API (`neuralshelf.main:app`) |
| `worker` | Processes the ingestion job queue (`neuralshelf.workers.ingestion_worker`); scale with `--scale worker=N` |

## Development without Docker for the app

```bash
cd backend
python -m venv .venv && .venv/bin/pip install -e ".[dev]"
docker compose up -d db
.venv/bin/alembic upgrade head
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
