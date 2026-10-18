# ALEX — AI Knowledge & Research Assistant

**Research your documents. Continue the conversation. Return to your work.**

ALEX combines document-grounded question answering with persistent conversations in a
React interface. Upload research material, ask follow-up questions, inspect retrieved
sources, and reopen earlier chats with their existing context. A FastAPI backend uses
LangGraph, Google Gemini, and PostgreSQL with pgvector to coordinate retrieval,
generation, authentication, and history.

[![CI](https://github.com/ankesh15/Alex/actions/workflows/ci.yml/badge.svg)](https://github.com/ankesh15/Alex/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)
![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-pgvector-4169E1?logo=postgresql&logoColor=white)

[Getting started](#getting-started) · [Architecture](#architecture) ·
[API reference](#api-reference) · [Testing](#testing) · [Deployment](#deployment) ·
[Roadmap](#roadmap)

## Features

| Capability | What you can do |
| --- | --- |
| Document research | Ask questions across a conversation's documents or focus on one file. |
| General chat | Talk to Gemini without document retrieval. |
| Conversation memory | Ask follow-up questions using bounded, scope-specific dialogue context. |
| Persistent history | Create, rename, reopen, and delete conversations from a responsive sidebar. |
| Source references | Inspect retrieved filenames, page numbers when available, and similarity scores. |
| Document ingestion | Upload PDF, DOCX, and TXT files, with a configurable size limit. |
| Authentication | Sign up, sign in, and sign out using revocable server-side cookie sessions. |
| User isolation | Access only your own conversations, exchanges, and documents. |

Conversation lists and message history are paginated. Switching chats guards against
late responses appearing in the wrong conversation. Starting a new chat retains
previous messages and attached documents.

Streaming responses, hybrid search, and an automated RAG evaluation framework are
planned; they are not part of the current implementation.

## Architecture

```mermaid
flowchart TD
    Browser[React · Vite · Tailwind CSS] --> API[FastAPI · Authentication · Ownership checks]
    API --> History[Conversation and memory services]
    History --> DB[(PostgreSQL + pgvector)]
    API --> Upload[Document extraction and chunking]
    Upload --> Embed[FastEmbed · Local embeddings]
    Embed --> DB
    Upload --> Files[Persistent document storage]
    API --> Graph[LangGraph RAG workflow]
    Graph --> DB
    Graph --> Gemini[Google Gemini]
    API --> General[General chat with scoped memory]
    General --> Gemini
```

### Document question answering

1. **Ingest:** Validate the upload, extract text, and split it into overlapping chunks.
   FastEmbed generates embeddings locally; PostgreSQL stores document metadata,
   chunks, and vectors. Original files stay in configured document storage.
2. **Contextualize:** Load recent successful exchanges from the current conversation
   and retrieval scope. LangGraph uses that context to resolve follow-up references.
3. **Retrieve:** Embed the question and search owner-authorized documents with
   pgvector cosine distance. Apply conversation/document filters and a relevance threshold.
4. **Generate:** Give Gemini the retrieved context. If no relevant context is found,
   return an insufficient-context response instead of generating a document answer.
5. **Persist:** Store a completed exchange atomically with its scope, citations, and
   token usage. Revision checks reject competing stale writes with HTTP 409.

Citations identify retrieved sources; they do not independently verify every generated
claim. Conversation history helps interpret questions and is not treated as document evidence.

### Memory and history

The existing `conversations` and `conversation_turns` tables are the single source of
truth for both memory and displayed history. General chat, all-document research, and
specific-document research have separate memory scopes. Prompt history is bounded by
turn count and character budget; full completed exchanges remain stored until deletion.

The frontend restores the last selected conversation by a per-user ID preference.
Messages are fetched from the authenticated API rather than stored in browser storage.
Chat requests without a `chat_id` remain stateless for conversation memory and still
require authentication.

### Technology stack

| Layer | Technologies |
| --- | --- |
| Frontend | React 18, Vite 5, Tailwind CSS 3, Lucide |
| API and validation | Python 3.11+, FastAPI, Pydantic, Uvicorn |
| AI orchestration | Google Gemini, LangGraph, LangChain |
| Embeddings | FastEmbed, `BAAI/bge-small-en-v1.5`, 384 dimensions by default |
| Data and storage | PostgreSQL 16, pgvector, SQLAlchemy, psycopg2, filesystem storage |
| Document processing | PyMuPDF, python-docx, LangChain text splitters |
| Infrastructure | Docker, Docker Compose, GitHub Actions, Railway and Vercel configuration |

Redis and Celery are configured for background processing infrastructure. The current
upload endpoint performs extraction and embedding during the request.

## Getting started

### Prerequisites

- Python 3.11 or newer.
- Node.js 18 or newer and npm.
- Docker with Docker Compose v2, or an existing PostgreSQL instance with pgvector.
- A Google Gemini API key for live answers.

The first embedding request may download the FastEmbed model. Subsequent requests
reuse its local cache.

### 1. Clone and install the backend

```bash
git clone https://github.com/ankesh15/Alex.git
cd Alex
python3 -m venv venv
source venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

On Windows, activate the virtual environment with `venv\Scripts\Activate.ps1` in PowerShell.

Edit `.env` for your environment. For the local Docker database and an HTTP frontend:

```dotenv
GOOGLE_API_KEY=your_google_api_key
DATABASE_URL=postgresql+psycopg2://postgres:postgrespassword@localhost:5432/alex_db
APP_ENV=development
SESSION_COOKIE_SECURE=false
SESSION_COOKIE_SAMESITE=lax
ALLOWED_ORIGINS=http://localhost:5173
FRONTEND_URL=http://localhost:5173
STORAGE_DIR=storage/documents
```

The database credentials above match the Compose development defaults. Use your own
credentials for a shared or production environment. Keep `.env` out of version control.

### 2. Start PostgreSQL and apply migrations

```bash
docker compose up -d postgres
docker compose ps
```

Wait for PostgreSQL to report healthy, then run:

```bash
python -m app.core.migrate
uvicorn app.api.main:app --host 127.0.0.1 --port 8000 --reload
```

The migration command applies the memory, authentication, and history migrations.
Run it before starting an upgraded installation. API startup rejects a partially
migrated ownership or history schema.

### 3. Start the frontend

In a separate terminal, from the repository root:

```bash
cd frontend
npm ci
cp .env.example .env
npm run dev
```

The frontend example sets `VITE_API_URL=http://localhost:8000`. Use `localhost`
consistently in the frontend URL, API URL, and allowed origins for local cookie authentication.

| Service | Local address |
| --- | --- |
| Application | [localhost:5173](http://localhost:5173) |
| API documentation | [localhost:8000/docs](http://localhost:8000/docs) |
| Alternative API documentation | [localhost:8000/redoc](http://localhost:8000/redoc) |
| Liveness endpoint | [localhost:8000/health](http://localhost:8000/health) |

Create an account, start a conversation, and choose **General**, **All Documents**, or
a specific attached document in the composer. Use **Chat history** to return to earlier work.

## Configuration

The complete backend and frontend templates are in [.env.example](.env.example) and
[frontend/.env.example](frontend/.env.example). Frontend `VITE_` values are public
build-time settings; keep Gemini and database credentials on the backend.

| Setting | Default or purpose |
| --- | --- |
| `GOOGLE_API_KEY` | Required for live Gemini generation. |
| `GEMINI_MODEL` | `gemini-2.5-flash` |
| `DATABASE_URL` | PostgreSQL connection string; use your deployment's credentials. |
| `STORAGE_DIR` | `storage/documents`; use persistent storage in production. |
| `MAX_UPLOAD_SIZE_MB` | `20`; the current frontend also enforces a 20 MB limit. |
| `ALLOWED_ORIGINS` | Explicit, comma-separated frontend origins. |
| `FRONTEND_URL` | Optional frontend origin added to the CORS allowlist. |
| `VITE_API_URL` | Frontend API origin, such as `http://localhost:8000`, without `/api/v1`. |

Plain `postgres://` and `postgresql://` URLs explicitly select the installed
`psycopg2-binary` driver. URLs that name another driver are preserved and require
that driver's package. CI also uses `postgresql+psycopg2://` explicitly.

### Retrieval and memory

| Setting | Default |
| --- | --- |
| `EMBEDDING_MODEL` / `EMBEDDING_DIMENSION` | `BAAI/bge-small-en-v1.5` / `384` |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | `1000` / `150` characters |
| `RAG_TOP_K` | `5` |
| `RAG_SIMILARITY_THRESHOLD` | `0.48` maximum cosine distance; lower is closer. |
| `MEMORY_MAX_TURNS` | `8` successful exchanges per conversation and scope. |
| `MEMORY_MAX_CHARS` | `12000` characters; not an exact token limit. |

### Sessions and authentication

| Setting | Default |
| --- | --- |
| `APP_ENV` | `development`; use `production` for deployment. |
| `SESSION_COOKIE_SECURE` | `true`; the local HTTP template explicitly sets `false`. |
| `SESSION_COOKIE_SAMESITE` | `lax`; `none` requires Secure cookies. |
| `SESSION_MAX_AGE_SECONDS` / `SESSION_IDLE_SECONDS` | `604800` / `43200` |
| `AUTH_RATE_MAX_ATTEMPTS` / `AUTH_RATE_WINDOW_SECONDS` | `20` attempts / `300` seconds. |

## API reference

The API prefix is `/api/v1`. Interactive request and response schemas are available
at `/docs` when the backend is running.

Protected routes require the session cookie. Protected mutations also require the
session's `X-CSRF-Token`; `/auth/me` restores the token for an active session.
Login and signup establish sessions and enforce origin and rate-limit checks.

| Area | Method and route | Purpose |
| --- | --- | --- |
| Authentication | `POST /auth/signup` | Create an account and session. |
| Authentication | `POST /auth/login` | Start a new session. |
| Authentication | `GET /auth/me` | Retrieve the current user and CSRF token. |
| Authentication | `POST /auth/logout` | Revoke the current session. |
| Chat | `POST /chat` | Query authorized documents. |
| Chat | `POST /chat/general` | Chat without document retrieval. |
| History | `POST /conversations` | Create a conversation with an optional title. |
| History | `GET /conversations` | List owned conversations with cursor pagination. |
| History | `GET /conversations/{id}` | Retrieve metadata and the last saved scope. |
| History | `PATCH /conversations/{id}` | Rename a conversation. |
| History | `DELETE /conversations/{id}` | Delete a conversation and its attached content. |
| History | `GET /conversations/{id}/messages` | Retrieve paginated user/assistant exchanges. |
| History | `GET /chat/{chat_id}/history` | Retrieve the compatible turn-based history view. |
| Documents | `POST /documents/upload` | Upload a file with an optional `chat_id`. |
| Documents | `GET /documents` | List owned documents, optionally filtered by `chat_id`. |
| Documents | `GET /documents/{document_id}` | Retrieve document details. |
| Documents | `DELETE /documents/{document_id}` | Delete a document and its chunks. |
| Documents | `DELETE /documents/chat/{chat_id}` | Delete a conversation's attached documents only. |

Conversation lists accept `limit` and `cursor`, returning `next_cursor`. Message
history accepts `limit`, `before_turn`, and `through_turn`. Its limit counts complete
exchanges, so 25 exchanges can return 50 individual messages. Use `next_before_turn`
for the next page and preserve the initial `through_turn` upper bound. Both pagination
limits range from 1 to 100.

A document-chat request can include:

```json
{
  "question": "What evidence supports the conclusion?",
  "chat_id": "your_conversation_id",
  "document_id": null,
  "top_k": 5
}
```

Conversation and document IDs select resources; the server independently verifies
ownership. Missing, foreign, quarantined, or deleted conversation IDs return 404 for
management/history operations. The existing chat endpoints can create a previously
unknown ID for the authenticated owner; they cannot claim an existing foreign,
unowned, or deleted ID.

## Security and data lifecycle

- Passwords use salted scrypt hashing. Opaque session tokens are stored as hashes in
  PostgreSQL, with absolute/idle expiration and logout revocation.
- Cookies are HttpOnly. Secure mode uses the `__Host-alex_session` cookie name.
  Mutation requests validate CSRF and origins; credentialed CORS uses explicit origins.
- Queries enforce authenticated ownership. PostgreSQL composite foreign keys also
  constrain conversation/message and conversation/document owner relationships.
- Legacy records without owners remain quarantined and cannot be claimed by presenting an ID.
- Uploads check extension, size, and nonempty content. UUID storage names and resolved
  path checks protect filesystem boundaries. MIME/signature validation remains planned.

**New Chat preserves earlier work.** Confirmed conversation deletion removes its
exchanges, document text, vector chunks, and attached files. File cleanup failures
leave inaccessible cleanup records and support retry through the same owner's DELETE
request. A minimal conversation tombstone prevents late requests from recreating it.
Unattached documents and other conversations are unaffected.

Linked RAG audit question/answer text is scrubbed during conversation deletion;
operational metrics remain. Older audit rows without a reliable conversation link
and backup copies require a separate operational retention policy. See the
[history design and deletion semantics](docs/feature5-history.md) for details.

## Testing

Run backend checks from the repository root with the virtual environment active:

```bash
python -m pip install pytest pytest-cov flake8 httpx
python -m pytest tests/ -v --cov=app --cov-report=term-missing
python -m flake8 app --jobs=1 --count --select=E9,F63,F7,F82 --show-source --statistics
```

Most tests use SQLite with mocked Gemini calls. Embedding tests require a cached or
downloadable FastEmbed model. PostgreSQL-specific tests skip unless
`MEMORY_TEST_DATABASE_URL` points to a **disposable database named `alex_memory_test*`**.
Never point it at an application database.

After setting that variable securely in your shell:

```bash
python -m pytest tests/test_memory_postgres.py tests/test_auth_postgres.py tests/test_history_postgres.py -v
```

Frontend checks, from `frontend/`:

```bash
npm test
npm run build
```

Coverage includes authentication, ownership, memory isolation, pagination, deletion,
reopening, and stale asynchronous responses. There is currently no frontend lint
script. GitHub Actions runs backend lint/tests and Docker build validation; frontend
and optional PostgreSQL integration checks are not yet included in that workflow.

## Deployment

### Backend

The [Dockerfile](Dockerfile) builds the FastAPI service, and [railway.json](railway.json)
configures Railway startup and liveness checks. Provision PostgreSQL with pgvector
and a persistent document-storage volume.

Before rolling out an upgraded backend:

1. Back up the database and document storage using your operational procedures.
2. Configure the intended database credentials and persistent `STORAGE_DIR`.
3. Run `python -m app.core.migrate` in the release environment before starting the new API.
4. Set `APP_ENV=production`, `SESSION_COOKIE_SECURE=true`, trusted frontend origins,
   and HTTPS. The container listens on the supplied `PORT` (default `8000`).

Migrations 001–003 are additive and repeatable. They preserve existing records and
leave unowned legacy data quarantined. No destructive rollback migration is provided.

Docker Compose is a development stack with bind mounts and a reload-enabled web
service. If running its API container, configure `DATABASE_URL` to use the `postgres`
service hostname rather than `localhost`; Redis/Celery URLs likewise use `redis`.
Run the migration command inside the configured web image before starting the API.

### Frontend

For Vercel, use `frontend` as the project root, `npm run build` as the build command,
and `dist` as the output directory. Set `VITE_API_URL` to the backend's public origin.
[frontend/vercel.json](frontend/vercel.json) contains SPA rewrites.

Prefer same-site custom domains or a same-origin API proxy for cookie authentication.
Cross-site deployments require `SESSION_COOKIE_SAMESITE=none` and Secure cookies;
browser third-party-cookie policies may still block sessions.

`GET /health` is a liveness endpoint, not a continuous database-readiness check.

## Project structure

```text
Alex/
├── app/
│   ├── agents/                # LangGraph workflow and state
│   ├── api/                   # FastAPI schemas, dependencies, and v1 endpoints
│   ├── config.py              # Environment-backed settings
│   ├── core/                  # Database, migrations, authentication, and Gemini client
│   ├── models/                # Users, sessions, conversations, turns, documents, and audit
│   ├── services/              # Memory, history, authorization, ingestion, and retrieval
│   └── tasks/                 # Celery task modules
├── frontend/
│   ├── src/auth/              # Authentication provider and screens
│   ├── src/components/        # Chat, history sidebar, documents, and citations
│   ├── src/services/          # Credentialed API client
│   ├── src/state/             # Conversation workspace controller and React hook
│   └── tests/                 # API and workspace regression tests
├── migrations/                # Additive SQL migrations 001–003
├── tests/                     # Backend unit and integration tests
├── docs/                      # Architecture decisions and implementation reports
├── .github/workflows/         # CI checks
├── .env.example               # Backend configuration template
├── docker-compose.yml         # Local PostgreSQL, Redis, API, and worker services
├── Dockerfile
└── requirements.txt
```

## Roadmap

- Token streaming, cancellation, and incremental response rendering.
- Hybrid vector/full-text retrieval with configurable result fusion.
- Reproducible RAG evaluation for retrieval, faithfulness, citations, and latency.
- Background document ingestion using the configured worker infrastructure.
- Email verification, account recovery, and additional identity protections.
- Scheduled cleanup retries, storage quotas, and operational retention tooling.

Current limitations include synchronous ingestion, no cross-tab live synchronization,
and no published production-scale retrieval or answer-quality benchmarks.

## Documentation and contributing

- [Repository review and upgrade plan](docs/upgrade-plan.md)
- [Conversation memory](docs/feature1-memory.md)
- [Authentication and authorization](docs/feature4-authentication.md)
- [Persistent history, migrations, and deletion behavior](docs/feature5-history.md)

For contributions, open an issue describing the problem or proposed change, keep pull
requests focused, add regression coverage for behavior changes, and run the relevant
checks above. Update configuration examples and migration documentation when needed.
Do not include API keys, database credentials, uploaded files, or local database artifacts.
