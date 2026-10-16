# NeuralShelf backend

FastAPI + PostgreSQL/pgvector + Ollama. Users upload PDFs, a worker indexes
them, and users search and chat with their documents, with citations.

- **API reference** with request/response examples: [API.md](API.md)
- **Live OpenAPI docs:** http://localhost:8000/docs
- **Project overview:** [../README.md](../README.md)

## Run locally

Prerequisites: Docker, `make`, and [Ollama](https://ollama.com) running on the
host with the models pulled:

```bash
ollama pull nomic-embed-text
ollama pull qwen3.5:2b-q4_K_M
```

First run (from the repository root):

```bash
cp backend/.env.example backend/.env   # then set JWT_SECRET_KEY (32+ characters)
make setup                             # build, start db, migrate, seed, start api + worker + web
```

Seeded logins: `admin@neuralshelf.local / Admin!12345` (admin),
`demo@neuralshelf.local / Demo!12345`.

## Architecture

```
src/neuralshelf/
├── main.py                 FastAPI app: routers, middleware, error handlers
├── cli.py                  Management commands (migrate, seed, promote-admin, ...)
├── api/v1/router.py        Mounts every feature's router under /api/v1
├── core/                   Config, security (passwords, JWT), logging, errors,
│                           response envelope, request-ID middleware
├── db/                     Engine/sessions, model registry, Alembic migrations, seeders
├── features/               One package per feature
│   ├── auth/               Signup, login, refresh-token rotation, httpOnly cookies, rate limits
│   ├── users/              User model and repository
│   ├── documents/          Upload, storage, ingestion job queue, chunking
│   ├── retrieval/          Semantic search (pgvector HNSW)
│   ├── chat/               Conversations, grounded answers, SSE streaming
│   ├── admin/              Ingestion queue operations (admin only)
│   └── health/             Liveness and readiness
├── integrations/           Adapters: Ollama embeddings and chat, PDF parsing
└── workers/                The ingestion worker process
```

**Inside a feature:** `router.py` → `service.py` → `repository.py` → `models.py`.
- **Routers** are thin: they validate input (`schemas.py`), call a service and
  shape the response.
- **Services** hold the business rules.
- **Repositories** hold the queries, and every user-facing query is scoped to
  the current user.
- **Features** use each other only through their services or repositories,
  never through routers.

**Key design decisions**

| Area | How |
| --- | --- |
| Responses | One envelope: `{success, code, message, data: [...]}`; list endpoints add `pagination` |
| Auth | Short-lived access JWT (memory only on the web) and a rotating refresh token in an httpOnly, `SameSite=Strict` cookie. Reusing a refresh token revokes every session. Native apps can get tokens in the body (`X-Auth-Mode: token`) |
| Ownership | Every query is scoped to the authenticated user; other users' resources return 404 |
| Ingestion | The job queue lives in PostgreSQL (`ingestion_jobs`): jobs are enqueued in the same transaction as the document and claimed with `FOR UPDATE SKIP LOCKED`, under renewable leases (crashed workers' jobs are resumed). Completion is fenced to the lease owner, and failures retry with exponential backoff |
| Search | Cosine distance over `VECTOR(768)` with an HNSW index and pgvector's iterative scan, so per-user filtering still returns full results |
| Chat | Retrieval, then a prompt with numbered passages, then Ollama. Answers come complete or as Server-Sent Events. Nothing is saved unless the answer completes |
| Observability | `X-Request-ID` on every response and in every log line (`job:<id>` in the worker). JSON logs in production |

## Configuration

Settings come from environment variables (or `backend/.env`; see
[.env.example](.env.example)). They are defined and validated in
`src/neuralshelf/core/config.py`.

| Variable | Default | Notes |
| --- | --- | --- |
| `APP_ENV` | `development` | `production` makes the cookie HTTPS-only, requires a 32+ character JWT secret, and blocks destructive commands |
| `DATABASE_URL` | local Docker db | PostgreSQL with pgvector |
| `JWT_SECRET_KEY` | — (required) | Signs access tokens |
| `ACCESS_TOKEN_EXPIRE_MINUTES` / `REFRESH_TOKEN_EXPIRE_DAYS` | `30` / `7` | Token lifetimes |
| `CORS_ORIGINS` | `http://localhost:3000,http://localhost:5173` | Browser origins allowed to call the API (comma-separated) |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | |
| `OLLAMA_CHAT_MODEL` / `OLLAMA_EMBEDDING_MODEL` | `qwen3.5:2b-q4_K_M` / `nomic-embed-text` | Embeddings must be 768-dimensional |
| `LOG_LEVEL` / `LOG_FORMAT` | `INFO` / `text` | `json` in the production image |
| `UPLOAD_DIR` / `MAX_UPLOAD_SIZE_MB` | `backend/storage/uploads` / `20` | Uploaded files live on disk, outside PostgreSQL |
| `CHUNK_SIZE_CHARS` / `CHUNK_OVERLAP_CHARS` | `1000` / `150` | Chunking for retrieval |
| `RATE_LIMIT_*` | login 20/IP and 5/email, signup 5/IP, refresh 30/IP per 60 s | `RATE_LIMIT_ENABLED=false` turns them off |
| `JOB_LEASE_SECONDS` / `JOB_MAX_ATTEMPTS` | `120` / `5` | Worker leases and retries |

## Commands

Run `make` to list them all. Database commands run in a temporary api
container (`docker compose run --rm`), so no extra service is needed.

| Make | Same thing without make | What it does |
|---|---|---|
| `make up` | `docker compose up -d db && … migrate && docker compose up -d api worker web` | Start everything, applying pending migrations first |
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

**Safety:**
- `migrate:fresh`, `migrate:rollback` and `db:seed` refuse to run when
  `APP_ENV=production`.
- Concurrent `migrate` runs are serialized by a PostgreSQL advisory lock, so
  two deploys migrating at once is safe.

### Production deploys

1. Run `python -m neuralshelf.cli migrate` once as a release step (e.g. a CI/CD
   job, or `docker run --rm <image> python -m neuralshelf.cli migrate`).
2. Then roll out the api and worker containers.

Never use `fresh` or `seed` in production. The production image (`Dockerfile`)
is multi-stage, runs as a non-root user and logs JSON.

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
.venv/bin/ruff check src tests   # lint, including docstrings
```

If every integration test is **skipped**, PostgreSQL isn't reachable: start
Docker Desktop and run `make up`.

CI (`.github/workflows/backend-ci.yml`) runs lint, migrations from an empty
database, `alembic check`, the rollback/fresh/seed commands, the test suite
and a production image build.

## Documentation conventions

- **What to document:** every public module, class, function and method has a
  docstring in **Google style**. Ruff's `D` rules enforce this
  (`pyproject.toml`). `__init__` is documented on its class; tests are
  documented by their names.
- **What to write:** behaviour and intent, such as what it does, rules,
  side effects (e.g. "flushed, not committed"), and anything surprising.
  Don't repeat the type hints.
- **Sections:** add `Args:`, `Returns:` and `Raises:` only when they say
  something the signature doesn't, for example:

  ```python
  def get(self, *, user_id: UUID, document_id: UUID) -> Document:
      """The user's document.

      Raises:
          DocumentNotFoundError: Missing, or owned by another user.
      """
  ```

- **Endpoints:** endpoint docstrings become the operation descriptions in
  Swagger. The first line is the summary users see.
- **API.md:** when an endpoint's contract changes, update [API.md](API.md)
  too.
