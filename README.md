# NeuralShelf

**Your knowledge, connected.** Upload PDFs, search them by meaning, and ask
questions. You get answers grounded in your own documents, with the document
and page for every source, typed or spoken.

Everything runs on your own machine: PostgreSQL with pgvector for search, and
Ollama for the language and embedding models.

## What it does

- **Documents:** upload PDFs. A background worker extracts, chunks and indexes
  them, with retries and crash recovery.
- **Semantic search:** find passages by meaning across your documents.
- **AI chat:** answers stream word by word, cite their sources, and say so
  when the documents don't contain the answer.
- **Voice:** ask by voice (Web Speech API) and hear answers read aloud by a
  Piper voice running in the browser. Speech starts ~300 ms after the first
  words of an answer.
- **Admin:** monitor the ingestion queue and retry failed jobs.
- **Security:** httpOnly-cookie sessions, CSRF protection, rate-limited
  login, and per-user data isolation.

## Architecture

```
 Browser ── http://localhost:5173 ──► web (Vite + React)
                                        │  /api (same origin)
                                        ▼
                                     api (FastAPI) ──────────┐
                                        │                    │ embeddings, answers
                                        ▼                    ▼
                                  db (PostgreSQL          Ollama (on the host)
                                     + pgvector)             ▲
                                        ▲                    │
                                        │ job queue          │ embeddings
                                     worker (ingestion) ─────┘
```

| Service  | What it is                                                                              |
| -------- | --------------------------------------------------------------------------------------- |
| `web`    | React app (Vite dev server with hot reload), proxies `/api` to `api`                    |
| `api`    | FastAPI HTTP API (auth, documents, search, chat, admin)                                 |
| `worker` | Processes the ingestion job queue (stored in PostgreSQL); scale with `--scale worker=N` |
| `db`     | PostgreSQL 17 + pgvector                                                                |
| Ollama   | Runs on the host: `qwen3.5:2b-q4_K_M` (answers), `nomic-embed-text` (embeddings)        |

## Quick start

Prerequisites: **Docker Desktop**, **make**, **Node 20.19+** (for editor
support and tests), and **[Ollama](https://ollama.com)** running on the host.

```bash
ollama pull nomic-embed-text
ollama pull qwen3.5:2b-q4_K_M

cp backend/.env.example backend/.env   # then set JWT_SECRET_KEY (32+ characters)
make setup                             # build, start the db, migrate, seed, start api + worker + web
make web-install                       # host dependencies for your editor, tests and Playwright
```

Open **http://localhost:5173** and sign in as `demo@neuralshelf.local` /
`Demo!12345`, or as admin `admin@neuralshelf.local` / `Admin!12345`. These
development accounts are created by the seeders and never exist in production.

| URL                        | What                           |
| -------------------------- | ------------------------------ |
| http://localhost:5173      | Web app                        |
| http://localhost:8000/docs | Interactive API docs (Swagger) |
| http://localhost:5050      | pgAdmin                        |

## Everyday commands

Run `make` to list them all.

| Command                                | Does                                                           |
| -------------------------------------- | -------------------------------------------------------------- |
| `make up` / `make down`                | Start everything (applying migrations) / stop it, keeping data |
| `make logs`                            | Follow api, worker and web logs                                |
| `make migrate` / `make migrate-status` | Apply pending migrations / list them                           |
| `make make-migration m="..."`          | Generate a migration from model changes                        |
| `make seed` / `make fresh-seed`        | Add dev data / **reset the database** and seed it              |
| `make admin email=you@example.com`     | Make a user an administrator                                   |
| `make test` / `make web-test`          | Backend tests / web lint, types and tests                      |
| `make web-e2e`                         | Browser end-to-end tests against the running stack             |
| `make gen-api`                         | Regenerate the web app's API types from the backend            |

## Repository layout

```
.
├── backend/              FastAPI API, ingestion worker, migrations, CLI  → backend/README.md
│   └── API.md            Every endpoint with request and response examples
├── apps/
│   ├── web/              React web app                                 → apps/web/README.md
│   └── mobile/           (planned)
├── infra/init.sql        Creates the pgvector extension on a new database volume
├── docker-compose.yml    Local development stack
├── Makefile              Developer commands
└── .github/workflows/    CI: backend-ci.yml, web-ci.yml
```

## Documentation

| Read                                     | For                                                    |
| ---------------------------------------- | ------------------------------------------------------ |
| [backend/README.md](backend/README.md)   | Backend architecture, configuration, commands, testing |
| [backend/API.md](backend/API.md)         | API reference: endpoints, payloads, responses, errors  |
| [apps/web/README.md](apps/web/README.md) | Web app structure, auth, voice, testing                |
| http://localhost:8000/docs               | Live OpenAPI docs, generated from the code             |

**In the code:** every public module, class and function is documented.
Python uses Google-style docstrings and TypeScript uses TSDoc. The linters
enforce both (Ruff `D` rules, `eslint-plugin-jsdoc`), so documentation can't
silently fall behind. Docs explain behaviour and the reasons for it; they don't
repeat what the type signatures already say. API endpoint docstrings appear in
Swagger.

## Quality checks

- **Backend:** Ruff (incl. docstrings) and pytest. Integration tests run
  against real PostgreSQL, and evaluation tests run against real Ollama.
- **Web:** Prettier, ESLint (feature boundaries, docs), strict TypeScript,
  Vitest and Playwright.
- **CI** runs all of these on every push and pull request, plus migrations
  from an empty database and a production image build.

## Troubleshooting

| Symptom                                    | Fix                                                                 |
| ------------------------------------------ | ------------------------------------------------------------------- |
| Backend tests are all "skipped"            | Docker isn't running: start Docker Desktop, then `make up`          |
| Answers or uploads fail with "unavailable" | Ollama isn't running on the host, or the models aren't pulled       |
| Voice answers never start                  | Run `npm run voice:setup` in `apps/web` (downloads the voice model) |
| Port 5173 already in use                   | Stop a local `npm run dev`, or `docker compose stop web`            |

## Before production

- **Configuration:** set `APP_ENV=production` (makes the cookie HTTPS-only and
  enforces a strong JWT secret) and run migrations as a release step. See
  [backend/README.md](backend/README.md#production-deploys).
- **Serving the web app:** serve it and the API from one origin, with the
  cross-origin isolation headers described in
  [apps/web/README.md](apps/web/README.md#production).
- ⚠️ **Licences:** the Piper voice `navgurukul-ai/Indian_accent_60` has no
  published licence, and espeak-ng (used for phonemes) is GPL-3.0. Resolve
  both before distributing the app.
