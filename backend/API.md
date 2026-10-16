# NeuralShelf API Reference

Base URL: `http://localhost:8000/api/v1` (local). Interactive docs with a
"Try it out" button: `http://localhost:8000/docs`. Machine-readable schema:
`http://localhost:8000/openapi.json`.

Examples were captured from the running API, except the admin failed-job
and retry examples, which are illustrative (no job had failed at the time).

---

## Contents

1. [Conventions](#1-conventions)
2. [Health](#2-health)
3. [Authentication](#3-authentication)
4. [Documents](#4-documents)
5. [Search](#5-search)
6. [Conversations and chat](#6-conversations-and-chat)
7. [Admin: ingestion jobs](#7-admin-ingestion-jobs)
8. [Error codes](#8-error-codes)

### Endpoint summary

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/health/live` | – | Process is running |
| GET | `/health/ready` | – | API and database are ready |
| POST | `/auth/signup` | – | Create an account |
| POST | `/auth/login` | – | Get access + refresh tokens |
| POST | `/auth/refresh` | – | Exchange a refresh token for new tokens |
| POST | `/auth/revoke` | – | Log out (revoke a refresh token) |
| GET | `/auth/me` | User | Current user's profile |
| POST | `/documents` | User | Upload a PDF |
| GET | `/documents` | User | List my documents |
| GET | `/documents/{document_id}` | User | Document details and processing status |
| DELETE | `/documents/{document_id}` | User | Delete a document |
| POST | `/documents/{document_id}/reprocess` | User | Process a document again |
| POST | `/retrieval/search` | User | Search my documents by meaning |
| POST | `/conversations` | User | Start a conversation |
| GET | `/conversations` | User | List my conversations |
| GET | `/conversations/{conversation_id}` | User | Conversation details |
| DELETE | `/conversations/{conversation_id}` | User | Delete a conversation and its messages |
| GET | `/conversations/{conversation_id}/messages` | User | Message history |
| POST | `/conversations/{conversation_id}/messages` | User | Ask a question (complete answer) |
| POST | `/conversations/{conversation_id}/messages/stream` | User | Ask a question (answer streamed word by word) |
| GET | `/admin/ingestion-jobs` | Admin | List processing jobs |
| GET | `/admin/ingestion-jobs/stats` | Admin | Queue health |
| POST | `/admin/ingestion-jobs/{job_id}/retry` | Admin | Retry one failed job |
| POST | `/admin/ingestion-jobs/retry-failed` | Admin | Retry all failed documents |

---

## 1. Conventions

### Response envelope

Every JSON response has the same shape. **`data` is always a list**, even for a
single item; read single objects from `data[0]`.

```json
{
  "success": true,
  "code": "SUCCESS",
  "message": "Human-readable message.",
  "data": [ ... ]
}
```

List endpoints add `pagination`:

```json
{
  "success": true,
  "code": "SUCCESS",
  "message": "Documents retrieved successfully.",
  "data": [ ... ],
  "pagination": { "limit": 20, "offset": 0, "total": 1 }
}
```

Errors use the same envelope with `success: false`. Branch on **`code`**
(stable); show **`message`** to users. See [Error codes](#8-error-codes).

```json
{
  "success": false,
  "code": "DOCUMENT_NOT_FOUND",
  "message": "Document not found.",
  "data": []
}
```

Validation errors (422) list each invalid field in `data`:

```json
{
  "success": false,
  "code": "VALIDATION_ERROR",
  "message": "Request validation failed.",
  "data": [
    { "field": "name", "message": "String should have at least 2 characters" },
    { "field": "email", "message": "Please enter a valid email address." },
    { "field": "password", "message": "String should have at least 8 characters" }
  ]
}
```

### Authentication

Send the access token on every endpoint marked **User** or **Admin**:

```
Authorization: Bearer <access_token>
```

- **Access tokens** expire after 30 minutes (`expires_in` is in seconds).
  Keep them **in memory only**, never in `localStorage` or `sessionStorage`.
- **Refresh tokens** last 7 days and are **single-use**: each refresh rotates
  them. Reusing an old one is treated as theft: it fails, and every session of
  that user is logged out.
- **Suggested client flow:** on `401 UNAUTHORIZED`, call `/auth/refresh` once,
  then retry the request. If refresh fails, send the user to login. Make sure
  only one refresh runs at a time, across tabs too.

How the refresh token travels depends on the client:

| | Browsers (default) | Native apps (`X-Auth-Mode: token`) |
|---|---|---|
| Login/refresh response | Sets an **httpOnly** cookie `ns_refresh` (`SameSite=Strict`, `Path=/api/v1/auth`, `Secure` in production). **No `refresh_token` in the body.** | `refresh_token` in the body; no cookie. Store it in the OS keychain/keystore. |
| Calling `/auth/refresh` and `/auth/revoke` | No body. Send the cookie (`credentials: "include"` / `withCredentials: true`) **and** the header `X-NeuralShelf-CSRF: 1`. | Body `{ "refresh_token": "..." }`, plus the `X-Auth-Mode: token` header. |
| After a page reload | Call `/auth/refresh`: it returns a new access token **and the user**. | – |

Why: JavaScript can't read an httpOnly cookie, so an XSS bug can't steal the
refresh token. The CSRF header can't be added by another website, so other
sites can't make the browser use the cookie. A cookie request without the
header gets `403 CSRF_CHECK_FAILED`.

For local development, run the web app through the Vite proxy (same origin).
Cross-origin browsers must be listed in `CORS_ORIGINS`.

### Pagination

List endpoints accept `?limit=` (1–100, default 20) and `?offset=` (default 0).
Values out of range return 422.

### Common headers

| Header | Direction | Meaning |
|---|---|---|
| `X-Request-ID` | Response (optional in request) | Unique ID per request. Include it in bug reports; it appears in server logs. You may send your own (letters, digits, `.`, `_`, `-`; max 128 chars). |
| `Retry-After` | Response | On `429`, seconds to wait before retrying |
| `X-NeuralShelf-CSRF: 1` | Request | Required with the refresh cookie on `/auth/refresh` and `/auth/revoke` |
| `X-Auth-Mode: token` | Request | Native apps: refresh token in the body instead of a cookie |
| `WWW-Authenticate: Bearer` | Response | On `401` |

### Ownership

Users only ever see their own documents and conversations. Another user's ID
returns `404`, exactly like an ID that doesn't exist.

### Formats

IDs are UUID strings. Timestamps are ISO 8601 in UTC, e.g.
`"2026-10-15T09:16:43.543824Z"`.

---

## 2. Health

### GET `/health/live`

Liveness: the process responds. No auth.

**200**
```json
{
  "success": true,
  "code": "SERVICE_HEALTHY",
  "message": "NeuralShelf API is running.",
  "data": [{ "status": "alive" }]
}
```

### GET `/health/ready`

Readiness: the API can reach the database. No auth.

**200**
```json
{
  "success": true,
  "code": "SUCCESS",
  "message": "NeuralShelf API and database are ready.",
  "data": [{ "database": "connected" }]
}
```

**503** when the database is unreachable: `code: "SERVICE_NOT_READY"`, `data: [{ "database": "unavailable" }]`.

---

## 3. Authentication

### POST `/auth/signup`

Create an account. Rate limited: 5 per minute per IP.

**Request**

| Field | Type | Rules |
|---|---|---|
| `name` | string | 2–100 characters; extra spaces are collapsed |
| `email` | string | Valid email; stored lowercase |
| `password` | string | 8–128 characters |

```json
{ "name": "Asha Verma", "email": "asha@example.com", "password": "CorrectHorse!42" }
```

**201**
```json
{
  "success": true,
  "code": "SUCCESS",
  "message": "Account created successfully.",
  "data": [
    {
      "id": "b9679752-3c77-4bca-ae92-ad8bb48494eb",
      "name": "Asha Verma",
      "email": "asha@example.com",
      "is_admin": false
    }
  ]
}
```

**Errors:** `409 EMAIL_ALREADY_REGISTERED`, `422 VALIDATION_ERROR`, `429 RATE_LIMITED`.
Signup does not log the user in; call `/auth/login` next.

### POST `/auth/login`

Rate limited: 20 per minute per IP, and 5 per minute per email address.
Browsers receive the refresh token as the `ns_refresh` httpOnly cookie
(`Set-Cookie` header); native apps sending `X-Auth-Mode: token` receive it as
`refresh_token` in the body.

**Request**
```json
{ "email": "asha@example.com", "password": "CorrectHorse!42" }
```

**200** (browser; native apps also get `"refresh_token"`)
```json
{
  "success": true,
  "code": "SUCCESS",
  "message": "Login successful.",
  "data": [
    {
      "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
      "token_type": "bearer",
      "expires_in": 1800,
      "refresh_expires_at": "2026-10-22T09:16:43.459278+00:00",
      "user": {
        "id": "b9679752-3c77-4bca-ae92-ad8bb48494eb",
        "name": "Asha Verma",
        "email": "asha@example.com",
        "is_admin": false
      }
    }
  ]
}
```

**Errors:** `401 INVALID_CREDENTIALS` (same message for an unknown email and a
wrong password), `422 VALIDATION_ERROR`, `429 RATE_LIMITED`.

### POST `/auth/refresh`

Rotate the refresh token and get a new access token and the current user. Rate
limited: 30 per minute per IP.

**Browser request:** no body; the cookie is sent automatically.
```
POST /api/v1/auth/refresh
X-NeuralShelf-CSRF: 1
Cookie: ns_refresh=...        (added by the browser)
```

**Native request**
```json
{ "refresh_token": "b0EcDwqZlHiPkWDr4cRM8ayBChI7HBwfti-R2-254cRn..." }
```
with header `X-Auth-Mode: token`.

**200** (browser; a new cookie is set. Native apps also get `"refresh_token"`.)
```json
{
  "success": true,
  "code": "SUCCESS",
  "message": "Token refreshed successfully.",
  "data": [
    {
      "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
      "token_type": "bearer",
      "expires_in": 1800,
      "refresh_expires_at": "2026-10-22T09:16:43.534751+00:00",
      "user": {
        "id": "b9679752-3c77-4bca-ae92-ad8bb48494eb",
        "name": "Asha Verma",
        "email": "asha@example.com",
        "is_admin": false
      }
    }
  ]
}
```

**Errors:** `401 INVALID_REFRESH_TOKEN` (missing, unknown, expired, revoked or
reused), `403 CSRF_CHECK_FAILED` (cookie sent without the CSRF header),
`429 RATE_LIMITED`.

### POST `/auth/revoke`

Log out: revokes the refresh token on the server and clears the cookie. Always
returns 200, even with no or unknown token, so it never reveals whether a
token exists. The current access token stays valid until it expires; discard
it on the client.

**Browser request:** no body, header `X-NeuralShelf-CSRF: 1`.
**Native request:** `{ "refresh_token": "..." }`.

**200**
```json
{ "success": true, "code": "SUCCESS", "message": "Token revoked successfully.", "data": [] }
```

**Errors:** `403 CSRF_CHECK_FAILED` (cookie sent without the CSRF header).

### GET `/auth/me`

**200**
```json
{
  "success": true,
  "code": "SUCCESS",
  "message": "Profile retrieved successfully.",
  "data": [
    {
      "id": "b9679752-3c77-4bca-ae92-ad8bb48494eb",
      "name": "Asha Verma",
      "email": "asha@example.com",
      "is_admin": false
    }
  ]
}
```

**Errors:** `401 UNAUTHORIZED`.

---

## 4. Documents

### The document object

| Field | Type | Notes |
|---|---|---|
| `id` | UUID | |
| `filename` | string | Original filename, without any path |
| `content_type` | string \| null | `application/pdf` |
| `file_size_bytes` | integer \| null | |
| `status` | string | `uploaded` → `processing` → `completed` or `failed` |
| `error_message` | string \| null | User-friendly reason when `failed` |
| `created_at` | timestamp | |
| `updated_at` | timestamp \| null | |

**Processing.** An upload returns immediately with `status: "uploaded"`; a
background worker then extracts, chunks and indexes the text. Poll
`GET /documents/{id}` (every 2–3 seconds is fine) until the status is
`completed` or `failed`. Only `completed` documents appear in search and chat.
A temporary failure (e.g. the AI service is down) is retried automatically, up
to 5 attempts; the status stays `processing` meanwhile.

### POST `/documents`

Upload a PDF as `multipart/form-data` with one field, **`file`**.

- **Limits:** PDF only (checked by content, not just the name), max 20 MB, not
  password-protected.
- **Scanned PDFs:** image-only PDFs upload fine but end as `failed`, because
  there is no text to extract.

```bash
curl -X POST http://localhost:8000/api/v1/documents \
  -H "Authorization: Bearer <access_token>" \
  -F "file=@biology-notes.pdf;type=application/pdf"
```

```js
// Browser
const form = new FormData();
form.append("file", fileInput.files[0]);
await fetch(`${API}/documents`, { method: "POST", headers: { Authorization: `Bearer ${token}` }, body: form });
// Don't set Content-Type yourself; the browser adds the multipart boundary.
```

**202**
```json
{
  "success": true,
  "code": "SUCCESS",
  "message": "Document uploaded and queued for processing.",
  "data": [
    {
      "id": "bad963cf-41de-43a6-b7a0-49ec5144a341",
      "filename": "biology-notes.pdf",
      "content_type": "application/pdf",
      "file_size_bytes": 992,
      "status": "uploaded",
      "error_message": null,
      "created_at": "2026-10-15T09:16:43.543824Z",
      "updated_at": null
    }
  ]
}
```

**Errors:** `422 INVALID_FILE` (not a PDF, empty, unreadable, encrypted, no
pages; see `message`), `413 FILE_TOO_LARGE`, `401 UNAUTHORIZED`.

### GET `/documents?limit=20&offset=0`

My documents, newest first.

**200**
```json
{
  "success": true,
  "code": "SUCCESS",
  "message": "Documents retrieved successfully.",
  "data": [
    {
      "id": "bad963cf-41de-43a6-b7a0-49ec5144a341",
      "filename": "biology-notes.pdf",
      "content_type": "application/pdf",
      "file_size_bytes": 992,
      "status": "completed",
      "error_message": null,
      "created_at": "2026-10-15T09:16:43.543824Z",
      "updated_at": "2026-10-15T09:16:44.166085Z"
    }
  ],
  "pagination": { "limit": 20, "offset": 0, "total": 1 }
}
```

### GET `/documents/{document_id}`

**200**: a document object in `data[0]` (shape as above).

A failed document looks like:
```json
{
  "status": "failed",
  "error_message": "No extractable text was found. Scanned or image-only PDFs are not supported yet."
}
```

**Errors:** `404 DOCUMENT_NOT_FOUND`.

### DELETE `/documents/{document_id}`

Deletes the document, its indexed text and the stored file. Past chat answers
keep their text, but their citations will point to a document that no longer
exists.

**200**
```json
{ "success": true, "code": "SUCCESS", "message": "Document deleted successfully.", "data": [] }
```

**Errors:** `404 DOCUMENT_NOT_FOUND`.

### POST `/documents/{document_id}/reprocess`

Process the document again, for example after a failure. No request body.

**202**: the document in `data[0]`, with `status: "uploaded"`. Poll as after an upload.

**Errors:** `409 DOCUMENT_BUSY` (already queued or processing), `404 DOCUMENT_NOT_FOUND`.

---

## 5. Search

### POST `/retrieval/search`

Find the passages in my processed documents that are closest in meaning to a
query. Chat uses this internally; call it directly for a search screen.

**Request**

| Field | Type | Rules |
|---|---|---|
| `query` | string | 1–2000 characters, not blank |
| `top_k` | integer | 1–20, default 5 |
| `document_ids` | UUID[] | Optional, max 50. Search only these documents; empty means all. |

```json
{ "query": "Where does photosynthesis happen?", "top_k": 2, "document_ids": [] }
```

**200**: best match first. `score` is the similarity: closer to 1 means more relevant.
```json
{
  "success": true,
  "code": "SUCCESS",
  "message": "Search completed successfully.",
  "data": [
    {
      "chunk_id": 2727,
      "document_id": "bad963cf-41de-43a6-b7a0-49ec5144a341",
      "filename": "biology-notes.pdf",
      "chunk_index": 0,
      "page_number": 1,
      "content": "Photosynthesis takes place in the chloroplasts of plant cells. Chlorophyll absorbs sunlight.",
      "score": 0.867
    },
    {
      "chunk_id": 2728,
      "document_id": "bad963cf-41de-43a6-b7a0-49ec5144a341",
      "filename": "biology-notes.pdf",
      "chunk_index": 1,
      "page_number": 2,
      "content": "The French Revolution began in 1789 with the storming of the Bastille.",
      "score": 0.5645
    }
  ]
}
```

`page_number` can be `null`. An empty `data` list means no processed documents matched.

**Errors:** `404 DOCUMENT_NOT_FOUND` (a `document_ids` entry isn't yours),
`422 VALIDATION_ERROR`, `503 EMBEDDING_SERVICE_UNAVAILABLE`.

---

## 6. Conversations and chat

### The conversation object

| Field | Type | Notes |
|---|---|---|
| `id` | UUID | |
| `title` | string \| null | If created without a title, it is set from the first question |
| `created_at` | timestamp | |
| `updated_at` | timestamp | Last activity; lists are sorted by this |

### The message object

| Field | Type | Notes |
|---|---|---|
| `id` | UUID | |
| `conversation_id` | UUID | |
| `role` | string | `user` or `assistant` |
| `content` | string | The question or the answer |
| `created_at` | timestamp | |
| `citations` | Citation[] | Sources for assistant answers; empty for user messages |

**Citation**

| Field | Type | Notes |
|---|---|---|
| `number` | integer | Matches `[1]`, `[2]` markers in the answer text |
| `document_id` | UUID | |
| `filename` | string | |
| `page_number` | integer \| null | |
| `chunk_index` | integer | |
| `score` | number | Similarity to the question |
| `excerpt` | string | First 300 characters of the source passage |

### POST `/conversations`

**Request** (body optional)
```json
{ "title": "Biology revision" }
```

**201**
```json
{
  "success": true,
  "code": "SUCCESS",
  "message": "Conversation created successfully.",
  "data": [
    {
      "id": "7aa6d556-75c6-4755-8cdb-638f0becac72",
      "title": "Biology revision",
      "created_at": "2026-10-15T09:16:45.744409Z",
      "updated_at": "2026-10-15T09:16:45.744410Z"
    }
  ]
}
```

### GET `/conversations?limit=20&offset=0`

My conversations, most recently active first. **200**: conversation objects
with `pagination`.

### GET `/conversations/{conversation_id}`

**200**: a conversation object in `data[0]`. **Errors:** `404 CONVERSATION_NOT_FOUND`.

### DELETE `/conversations/{conversation_id}`

Deletes the conversation and all its messages.

**200**
```json
{ "success": true, "code": "SUCCESS", "message": "Conversation deleted successfully.", "data": [] }
```

### GET `/conversations/{conversation_id}/messages?limit=20&offset=0`

History, **oldest first**.

**200**
```json
{
  "success": true,
  "code": "SUCCESS",
  "message": "Messages retrieved successfully.",
  "data": [
    {
      "id": "6633699f-216a-41f1-a309-29688e0adbc3",
      "conversation_id": "7aa6d556-75c6-4755-8cdb-638f0becac72",
      "role": "user",
      "content": "Where does photosynthesis take place?",
      "created_at": "2026-10-15T09:16:45.763900Z",
      "citations": []
    },
    {
      "id": "fe4324f5-29e8-4419-a3a5-011b88dccab2",
      "conversation_id": "7aa6d556-75c6-4755-8cdb-638f0becac72",
      "role": "assistant",
      "content": "Photosynthesis takes place in the chloroplasts of plant cells [1].",
      "created_at": "2026-10-15T09:16:46.356780Z",
      "citations": [
        {
          "number": 1,
          "document_id": "bad963cf-41de-43a6-b7a0-49ec5144a341",
          "filename": "biology-notes.pdf",
          "page_number": 1,
          "chunk_index": 0,
          "score": 0.8869,
          "excerpt": "Photosynthesis takes place in the chloroplasts of plant cells. Chlorophyll absorbs sunlight."
        }
      ]
    }
  ],
  "pagination": { "limit": 20, "offset": 0, "total": 2 }
}
```

### POST `/conversations/{conversation_id}/messages`

Ask a question and wait for the complete answer. The question and answer are
saved together. If generation fails, nothing is saved and the request can be
retried.

**Request**

| Field | Type | Rules |
|---|---|---|
| `content` | string | 1–4000 characters, not blank |
| `top_k` | integer | 1–20, default 5: how many passages to use as sources |
| `document_ids` | UUID[] | Optional, max 50: answer only from these documents |

```json
{ "content": "Where does photosynthesis take place?", "top_k": 2, "document_ids": [] }
```

**201**
```json
{
  "success": true,
  "code": "SUCCESS",
  "message": "Answer generated successfully.",
  "data": [
    {
      "user_message": {
        "id": "6633699f-216a-41f1-a309-29688e0adbc3",
        "conversation_id": "7aa6d556-75c6-4755-8cdb-638f0becac72",
        "role": "user",
        "content": "Where does photosynthesis take place?",
        "created_at": "2026-10-15T09:16:45.763900Z",
        "citations": []
      },
      "assistant_message": {
        "id": "fe4324f5-29e8-4419-a3a5-011b88dccab2",
        "conversation_id": "7aa6d556-75c6-4755-8cdb-638f0becac72",
        "role": "assistant",
        "content": "Photosynthesis takes place in the chloroplasts of plant cells [1].",
        "created_at": "2026-10-15T09:16:46.356780Z",
        "citations": [
          {
            "number": 1,
            "document_id": "bad963cf-41de-43a6-b7a0-49ec5144a341",
            "filename": "biology-notes.pdf",
            "page_number": 1,
            "chunk_index": 0,
            "score": 0.8869,
            "excerpt": "Photosynthesis takes place in the chloroplasts of plant cells. Chlorophyll absorbs sunlight."
          },
          {
            "number": 2,
            "document_id": "bad963cf-41de-43a6-b7a0-49ec5144a341",
            "filename": "biology-notes.pdf",
            "page_number": 2,
            "chunk_index": 1,
            "score": 0.5497,
            "excerpt": "The French Revolution began in 1789 with the storming of the Bastille."
          }
        ]
      }
    }
  ]
}
```

If no relevant passage is found, the answer is: `"I couldn't find relevant
information in your documents to answer that question."` and `citations` is empty.

**Errors:** `404 CONVERSATION_NOT_FOUND`, `404 DOCUMENT_NOT_FOUND`,
`422 VALIDATION_ERROR`, `503 EMBEDDING_SERVICE_UNAVAILABLE`, `503 LLM_SERVICE_UNAVAILABLE`.

### POST `/conversations/{conversation_id}/messages/stream`

Same request body as above, but the answer arrives **word by word** as
[Server-Sent Events](https://developer.mozilla.org/docs/Web/API/Server-sent_events)
(`Content-Type: text/event-stream`), for a typing effect.

**Events, in order**

| Event | `data` | When |
|---|---|---|
| `start` | `{ "conversation_id", "citations": Citation[] }` | Once, first; render sources immediately |
| `token` | `{ "delta": "text" }` | Many; append each `delta` to the answer |
| `done` | `{ "user_message", "assistant_message" }` (same as the non-streaming response) | Once, last, after both messages are saved |
| `error` | `{ "code", "message" }` | Instead of `done` if generation fails; nothing is saved |

**Example stream** (tokens shortened)
```
event: start
data: {"conversation_id": "7aa6d556-75c6-4755-8cdb-638f0becac72", "citations": [{"number": 1, "document_id": "bad963cf-41de-43a6-b7a0-49ec5144a341", "filename": "biology-notes.pdf", "page_number": 2, "chunk_index": 1, "score": 0.9155, "excerpt": "The French Revolution began in 1789 with the storming of the Bastille."}]}

event: token
data: {"delta": "The"}

event: token
data: {"delta": " French"}

event: token
data: {"delta": " Revolution began in 1789 [1]."}

event: done
data: {"user_message": {...}, "assistant_message": {"id": "...", "role": "assistant", "content": "The French Revolution began in 1789 with the storming of the Bastille [1].", "citations": [...], ...}}
```

**Client notes**

- **Use `fetch`, not `EventSource`.** This is a POST with an `Authorization`
  header, which `EventSource` can't send. Read `response.body` with a stream
  reader and split events on blank lines (`\n\n`).
- **Errors before streaming starts** (wrong conversation, invalid body, search
  service down) come back as a normal JSON error response with the usual status
  code. Check `response.ok` before reading the stream.
- **Cancelling:** if the user closes the stream early, nothing is saved.
- **Saved IDs:** use the IDs in `done` as the saved message IDs.

```js
const res = await fetch(`${API}/conversations/${id}/messages/stream`, {
  method: "POST",
  headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
  body: JSON.stringify({ content: question }),
});
if (!res.ok) throw await res.json();               // normal error envelope

const reader = res.body.pipeThrough(new TextDecoderStream()).getReader();
let buffer = "";
for (;;) {
  const { value, done } = await reader.read();
  if (done) break;
  buffer += value;
  let split;
  while ((split = buffer.indexOf("\n\n")) !== -1) {
    const block = buffer.slice(0, split);
    buffer = buffer.slice(split + 2);
    const event = block.match(/^event: (.*)$/m)[1];
    const data = JSON.parse(block.match(/^data: (.*)$/m)[1]);
    if (event === "start") showSources(data.citations);
    if (event === "token") appendToAnswer(data.delta);
    if (event === "done") saveMessages(data);
    if (event === "error") showError(data.message);
  }
}
```

---

## 7. Admin: ingestion jobs

Requires a user with `is_admin: true`; others get `403 FORBIDDEN`. Admins are
created on the server (`make admin email=...`), never through the API.

Each upload or reprocess creates one **ingestion job**. Job `status` is
`queued`, `running`, `succeeded` or `failed`. A document can have several jobs
over time (history); at most one is queued or running.

### GET `/admin/ingestion-jobs?status=failed&limit=20&offset=0`

Newest first. `status` is optional: `queued`, `running`, `succeeded` or `failed`.

**200**
```json
{
  "success": true,
  "code": "SUCCESS",
  "message": "Ingestion jobs retrieved successfully.",
  "data": [
    {
      "id": "a19f9c49-2e22-4ded-ad74-7ae180f08dfd",
      "document_id": "bad963cf-41de-43a6-b7a0-49ec5144a341",
      "user_id": "b9679752-3c77-4bca-ae92-ad8bb48494eb",
      "filename": "biology-notes.pdf",
      "status": "failed",
      "attempts": 5,
      "max_attempts": 5,
      "last_error": "EmbeddingServiceError: The embedding service is currently unavailable.",
      "locked_by": null,
      "available_at": "2026-10-15T09:16:44.621459Z",
      "created_at": "2026-10-15T09:16:44.621459Z",
      "updated_at": "2026-10-15T09:21:02.719105Z"
    }
  ],
  "pagination": { "limit": 20, "offset": 0, "total": 1 }
}
```

- `last_error` is the internal technical error; it is only exposed to admins.
- `locked_by` is the worker currently processing a `running` job.

### GET `/admin/ingestion-jobs/stats`

**200**
```json
{
  "success": true,
  "code": "SUCCESS",
  "message": "Ingestion job statistics retrieved successfully.",
  "data": [
    {
      "counts": { "queued": 0, "running": 0, "succeeded": 3, "failed": 0 },
      "oldest_due_job_age_seconds": 0.0,
      "running_with_expired_lease": 0
    }
  ]
}
```

- **`oldest_due_job_age_seconds`:** how long the oldest waiting job has been
  ready to run. If it keeps growing, workers are down or overloaded.
- **`running_with_expired_lease`:** jobs whose worker seems to have died. They
  are picked up again automatically.

### POST `/admin/ingestion-jobs/{job_id}/retry`

Queue a new attempt for a **failed** job's document. The failed job stays as
history. No body.

**202**
```json
{
  "success": true,
  "code": "SUCCESS",
  "message": "Document queued for another ingestion attempt.",
  "data": [
    { "job_id": "5d0c1f3e-8a51-4b6e-9f7d-2c3b4a5e6f70", "document_id": "bad963cf-41de-43a6-b7a0-49ec5144a341" }
  ]
}
```

**Errors:** `404 JOB_NOT_FOUND`, `409 JOB_NOT_FAILED` (job didn't fail),
`409 DOCUMENT_BUSY` (document already has a pending job).

### POST `/admin/ingestion-jobs/retry-failed?limit=100`

Requeue every failed document that isn't already queued, for example after
fixing an outage. `limit` is 1–500, default 100. No body.

**202**
```json
{
  "success": true,
  "code": "SUCCESS",
  "message": "Failed documents queued for another ingestion attempt.",
  "data": [
    { "requeued": 2, "document_ids": ["bad963cf-41de-43a6-b7a0-49ec5144a341", "0f6e1d2c-..."] }
  ]
}
```

---

## 8. Error codes

| HTTP | `code` | Meaning / what the client should do |
|---|---|---|
| 401 | `UNAUTHORIZED` | Missing, invalid or expired access token. Refresh, then retry once. |
| 401 | `INVALID_CREDENTIALS` | Wrong email or password |
| 401 | `INVALID_REFRESH_TOKEN` | Refresh token unusable. Send the user to login. |
| 403 | `FORBIDDEN` | Logged in but not allowed (admin endpoints) |
| 403 | `CSRF_CHECK_FAILED` | Cookie-based refresh/revoke without the `X-NeuralShelf-CSRF: 1` header |
| 404 | `NOT_FOUND` | Unknown URL |
| 404 | `DOCUMENT_NOT_FOUND` | Document doesn't exist or isn't yours |
| 404 | `CONVERSATION_NOT_FOUND` | Conversation doesn't exist or isn't yours |
| 404 | `JOB_NOT_FOUND` | Admin: unknown job |
| 405 | `METHOD_NOT_ALLOWED` | Wrong HTTP method for this URL |
| 409 | `EMAIL_ALREADY_REGISTERED` | Signup with an existing email |
| 409 | `DOCUMENT_BUSY` | Document is already queued or processing |
| 409 | `JOB_NOT_FAILED` | Admin: only failed jobs can be retried |
| 413 | `FILE_TOO_LARGE` | Upload over 20 MB |
| 422 | `VALIDATION_ERROR` | Invalid input. Field details are in `data`. |
| 422 | `INVALID_FILE` | Not a usable PDF. Show `message`. |
| 429 | `RATE_LIMITED` | Too many attempts. Wait `Retry-After` seconds. |
| 500 | `INTERNAL_SERVER_ERROR` | Unexpected error. Report the `X-Request-ID`. |
| 503 | `SERVICE_NOT_READY` | Readiness check failed (database down) |
| 503 | `EMBEDDING_SERVICE_UNAVAILABLE` | AI search service down. Retry later. |
| 503 | `LLM_SERVICE_UNAVAILABLE` | AI answer service down. Retry later. |
