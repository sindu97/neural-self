# NeuralShelf web

React app for NeuralShelf: upload PDFs, search them by meaning, and chat with
them with cited answers, typed or spoken.

Project overview: [../../README.md](../../README.md). API reference:
[../../backend/API.md](../../backend/API.md).

**Stack:** React 19 + TypeScript (strict), Vite, React Router, Tailwind CSS +
shadcn/ui, TanStack Query, Axios, React Hook Form + Zod, Lucide, Sonner.
**Voice:** Web Speech API (speech-to-text), Piper via onnxruntime-web +
phonemizer (text-to-speech, in the browser).
**Tests:** Vitest + Testing Library + MSW, and Playwright.

## Run

With Docker (recommended), from the repository root:

```bash
make up              # db, api, worker and web — open http://localhost:5173
make web-logs        # follow the Vite dev server
```

The `web` container runs the Vite dev server with **hot reload**: edits in
`apps/web/src` show up in the browser immediately. `/api` is proxied to the
`api` container, so the app and API share one origin.

- **Dependencies:** the container keeps its own `node_modules` in a Docker
  volume, because some packages ship Linux-only binaries. It runs `npm ci` by
  itself when `package-lock.json` changes. Run `make web-install` too, so your
  editor, the tests and Playwright have host dependencies.
- **If saving doesn't trigger a reload:** set `VITE_USE_POLLING=true` on the
  `web` service.

Without Docker for the web app (stop the container first: `docker compose stop web`):

```bash
npm install
npm run dev          # http://localhost:5173 — /api is proxied to http://localhost:8000
```

Seeded logins (after `make seed`): `demo@neuralshelf.local / Demo!12345`,
admin `admin@neuralshelf.local / Admin!12345`.

## Scripts

| Script                               | Does                                                            |
| ------------------------------------ | --------------------------------------------------------------- |
| `npm run dev`                        | Dev server with the API proxy                                   |
| `npm run build`                      | Type-check and build to `dist/`                                 |
| `npm run lint` / `npm run typecheck` | ESLint (incl. feature boundaries) / TypeScript                  |
| `npm test`                           | Unit and component tests (fake API via MSW; no backend needed)  |
| `npm run test:e2e`                   | Playwright against the real stack (backend + Ollama running)    |
| `npm run gen:api`                    | Regenerate `src/lib/api/schema.d.ts` from the backend's OpenAPI |
| `npm run format`                     | Prettier                                                        |

Run `npm run gen:api` whenever the backend API changes, then fix any type errors.
Those errors are where the frontend no longer matches the API.

## Structure

```
src/
├── app/            providers, router (lazy routes), query client, layout (shell, sidebar)
├── components/
│   ├── ui/         shadcn/ui components (themed in index.css)
│   ├── layout/     PageHeader, StatCard
│   ├── feedback/   ErrorBoundary, ErrorState, EmptyState, FullPageLoader
│   ├── forms/      FormField
│   └── brand/      logo
├── core/           validated env config, constants (routes, limits)
├── lib/
│   ├── api/        client.ts (Axios + refresh-on-401), session.ts, sse.ts (streaming),
│   │               errors.ts (ApiError), types.ts, schema.d.ts (generated)
│   ├── format.ts   dates, sizes
│   └── utils.ts    cn()
└── features/       auth, dashboard, documents, retrieval, chat, activity, settings, admin, voice
                    each: api/ components/ hooks/ pages/ (+ schemas/, utils/) and index.ts
```

**Feature rule (enforced by ESLint):** a feature imports another feature only
through its `index.ts`, e.g. `import { useDocumentLibrary } from '@/features/documents'`.
Inside a feature, use relative imports. Only `app/router.tsx` loads pages directly.

## Documentation conventions

- **What to document:** every exported function, component, hook, class and
  interface has a **TSDoc** comment (`/** ... */`). `eslint-plugin-jsdoc`
  enforces this in `npm run lint`. Generated shadcn/ui components and tests
  are exempt.
- **What to write:** what it does and why, plus behaviour that isn't obvious
  (side effects, caching, polling). **Never repeat types**: TypeScript has
  them, and `jsdoc/no-types` rejects `{type}` annotations.
- **Tags and links:** use `@remarks` for longer details and `{@link name}` to
  link related code. VS Code shows these on hover.

  ```ts
  /** The newest `limit` documents, polled while any of them is still processing. */
  export function useRecentDocuments(limit = 5) { ... }
  ```

- **Inline comments** (`//`) explain _why_ a line exists, not what it does.

## Authentication and security

- **Refresh token:** an **httpOnly** cookie (`SameSite=Strict`, scoped to
  `/api/v1/auth`). JavaScript can't read it, so XSS can't steal it.
- **Access token:** kept **in memory only** (`lib/api/session.ts`), never in
  `localStorage` or `sessionStorage`. After a reload, `AuthProvider` calls
  `/auth/refresh` to restore the session from the cookie.
- **Refresh-on-401:** the Axios client refreshes automatically and replays the
  request once. Refreshes are single-flight in a tab and serialized across tabs
  (Web Locks), because refresh tokens are single-use.
- **CSRF:** cookie requests send `X-NeuralShelf-CSRF: 1`, a header other
  sites cannot add.
- **Model answers:** rendered with `react-markdown`, which never renders raw HTML.
- **Route guards:** `RequireAuth` and `RequireAdmin` hide screens. The backend
  enforces the same rules (401/403), so they're for UX, not security.

## Voice (ask by voice, spoken answers)

- **Asking by voice:** the mic inside the question box uses the browser's
  **Web Speech API** (Chrome, Edge, Safari; not Firefox). Words appear as
  you speak, and the question sends itself after a 1 s pause. Tap the mic again
  to send now, or press Esc to cancel. Chrome runs recognition **on-device**
  when its language pack is installed; otherwise the browser's cloud service is used.
- **Spoken answers:** text-to-speech runs **in the browser** with the Piper
  voice `navgurukul-ai/Indian_accent_60`. In a Web Worker,
  `features/voice/tts/piper.worker.ts` converts text to espeak-ng phonemes
  (`phonemizer`), then to the voice's phoneme IDs, then runs the ONNX model
  (`onnxruntime-web`). Playback uses Web Audio.
- **When answers are read aloud:** answers to spoken questions are always
  read. Typed questions are read only with "Read answers aloud" on (saved per
  browser). Every answer has **Listen**, and while it plays, **Mute**, which
  stops it immediately.

**Latency** (measured; the `[voice]` logs in the dev console show it per answer):

|                                        |                                                                 |
| -------------------------------------- | --------------------------------------------------------------- |
| First words of an answer → first audio | ~300 ms (speech starts while the answer is still streaming)     |
| Listen → first audio                   | ~300 ms                                                         |
| Voice load, first time / cached        | ~4 s / ~1.5 s (61 MB model kept in the browser's Cache Storage) |

How it stays fast:

- The answer is spoken a sentence at a time while it streams, and the first
  piece is a short opening phrase.
- Synthesis runs in a worker with multi-threaded WASM, and a warm-up run
  happens right after loading.
- The model starts loading as soon as the user reaches for the mic.

**Requirements:**

- **Cross-origin isolation.** The dev and preview servers send
  `Cross-Origin-Opener-Policy: same-origin` and
  `Cross-Origin-Embedder-Policy: require-corp` (`vite.config.ts`).
  **Production must send them too**, or synthesis falls back to one thread
  (it still works, just slower).
- **The voice model.** `npm install` / `npm run voice:setup` downloads it
  (checksum-verified). It is git-ignored.
- ⚠️ **Licence:** the `Indian_accent_60` voice has no licence published
  upstream, and espeak-ng (inside `phonemizer`) is GPL-3.0. Resolve both
  before distributing the app.

## Production

Serve `dist/` (with the cross-origin isolation headers above) and the API from **one origin** (e.g. a reverse proxy routing
`/api` to the backend). That keeps cookies first-party and avoids CORS. If the
API is on another origin, set `VITE_API_BASE_URL` and add the web origin to the
backend's `CORS_ORIGINS`. Set the backend's `APP_ENV=production` so the cookie
is HTTPS-only (`Secure`).
