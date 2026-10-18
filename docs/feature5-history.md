# Feature 5: persistent chat history

Implemented as an independent increment after memory and authentication. No streaming,
hybrid retrieval, new dependencies, commits or deployment. Deployment configuration
files remain unchanged. [Changed-file manifest](feature5-files.md) and
[Feature 5 source patch](feature5-history-only.patch) separate this increment from
previous uncommitted work.

## Architecture before and after

Before: PostgreSQL already held owned `conversations` and atomic `conversation_turns`.
LangGraph and General chat loaded bounded, scope-specific successful turns and saved
with revision conflict detection. Cookie sessions, CSRF, composite ownership FKs and
NULL-owner quarantine already protected requests. React kept only the current view;
reload generated a new ID and New Chat deleted prior documents.

After: the same conversation and turn tables serve management, display and memory.
`ConversationService` provides owner-checked CRUD, keyset list pagination and a
message projection of existing exchanges. There is no second transcript/message table.
Titles, custom-title state, deletion timestamps and an owner/history index extend the
existing conversation model. The first completed question produces an 80-character
whitespace-normalized title; explicit titles can be 120 characters and survive later
saves. Rename affects display ordering, not the memory revision. Upload and completed
exchanges update the conversation timestamp.

React uses a tested workspace controller behind the existing authentication gate.
A collapsible desktop sidebar becomes a mobile drawer, with list pagination, title
and last-updated display, rename/delete dialogs, empty/error states and keyboard
focus handling. Reopening fetches the existing ID, latest saved exchanges and attached
documents; sending continues that ID's existing bounded memory. Reload remembers
only the last selected ID under a user-specific browser-storage key. Transcripts,
passwords, session tokens and CSRF tokens are not stored there. All reopen operations
validate ownership on the server. Logout unmounts the controller and invalidates work.

General, all-documents and specific-document memory remain separate. Reopening
restores the last saved turn's scope. If its specific document was removed, the UI
falls back to All Documents with a notice; it never silently switches to General.
Saved citations and token usage are reconstructed from the same turn rows. Existing
LangGraph nodes, bounded context and compare-and-swap persistence are preserved.

## API and pagination

Every route under `/api/v1/conversations` uses the existing server-authenticated
principal. POST/PATCH/DELETE use existing CSRF and origin checks. Extra JSON owner/ID
fields are rejected; selectors never grant ownership. Unknown, foreign, quarantined
or deleted IDs return 404 (repeat owner DELETE is the cleanup exception).

| Method | Route | Contract |
| --- | --- | --- |
| POST | `/conversations` | `{}` or optional `title`; server UUID; 201 metadata |
| GET | `/conversations` | `limit` 1–100 (default 25), opaque `cursor`; `conversations`, `next_cursor` |
| GET | `/conversations/{id}` | Metadata plus `last_scope` |
| PATCH | `/conversations/{id}` | Required normalized nonblank `title`, 1–120 characters |
| GET | `/conversations/{id}/messages` | `limit` 1–100 exchanges, optional `before_turn`, `through_turn`; chronological messages |
| DELETE | `/conversations/{id}` | `{id,status:"deleted",cleanup_pending:<count>}` |

List ordering is `(updated_at DESC, id DESC)` with a keyset cursor and owner predicate.
Cursors are validated data, never SQL or authorization. Concurrent updates can move a
conversation between pages; client deduplication avoids duplicate rows, and refreshing
starts again at page one. This is a live list, not a frozen global snapshot.

Message pages always contain complete user/assistant pairs. A limit of 25 yields up
to 50 messages; default 25, maximum 100 exchanges. Stable message IDs derive from the
turn ID and role. Latest pages and older pages are returned in chronological order.
The response's `next_before_turn` supplies the next `before_turn`; keep its initial
`through_turn` upper bound for older requests so newly completed exchanges don't
change that traversal. A new conversation returns an empty page. The compatible
`/chat/{id}/history` endpoint uses the same service and keeps its turn representation.

The existing document list remains unpaginated; only conversation lists and message
history are in this increment's pagination scope.

## Async correctness and deletion

Every selection has an increasing generation, including A → B → A. History, document,
upload and answer completions verify that generation before updating the view.
Switching clears the prior view immediately. An answer completed in the background
still belongs to its original server conversation; reopening that conversation
refreshes authoritative history. A per-conversation busy guard blocks a second local
submission against the same in-flight memory snapshot. Cross-tab concurrent saves
retain the existing HTTP 409 behavior. List requests have separate generation guards,
and deleted IDs cannot re-enter the list from late completions.

New Chat now retains earlier messages and attached documents. Explicit conversation
deletion requires UI confirmation and has these semantics:

1. Lock the owned parent row. Mark it deleted and advance its revision, remove all its
   owned exchanges, remove attached chunks/embeddings, clear document extracted text,
   filenames and errors, and scrub linked owned RAG audit input/output in one database
   transaction. Documents enter `DELETING`; all metadata and retrieval paths hide them.
2. Commit before unlinking files. Successful physical cleanup removes document rows.
   Failed cleanup retains inaccessible `DELETING` metadata and reports `cleanup_pending`.
   The UI provides Retry file cleanup; repeat owner DELETE safely retries. Resolved
   path containment prevents unlinking outside configured storage.
3. Keep only the conversation's ID/owner, revision, timestamps, deletion marker and
   generic deleted title. This tombstone prevents lazy chat creation or an old memory
   snapshot from resurrecting content. Deleted conversations have no restore API.

Unattached user documents (`chat_id=NULL`), other conversations and NULL-owner legacy
records are untouched. Newly linked RAG audit logs retain numeric/status metrics but
lose question/answer text; late logs also omit text for deleted parents. Earlier audit
logs have no trustworthy conversation link, so migration leaves them unchanged. An
operator must define a separate verified retention policy for those pre-increment
logs and backups. Deleting a document independently leaves its prior transcript and
citation metadata; deleting its conversation removes that transcript too.

Upload finalization takes the parent lock before committing parsed text/chunks;
deleted parents cannot be revived by an ingestion completion. Memory saves require
both owner/revision equality and an active parent. PostgreSQL checks exercise deletion
racing a memory save: either save finishes first and is then erased, or it conflicts.

## Safe migration and deployment procedure

`migrations/003_persistent_history.sql` is additive, transactional and repeatable.
It adds title/custom/deleted columns, the owner/history index, and an optional nullable
indexed audit `chat_id` FK. It backfills titles only from an owned conversation's
same-owner first turn. No existing messages/documents are deleted or reassigned.
NULL-owner records remain quarantined; signup cannot claim them. The SQLite migration
branch exists for tests; PostgreSQL is the production target.

Use the intended `DATABASE_URL` from trusted environment configuration. Back up the
PostgreSQL database and storage together using existing operational procedures. Run
all three migrations before restarting the upgraded API; startup refuses a partial
history schema. Repeated runs do not overwrite custom titles. Additive DDL still
acquires PostgreSQL table locks; schedule the upgrade appropriately for database size.
There is no destructive rollback migration. Backups retain their own deletion policy.

```bash
# Repository root; configure existing .env fields securely, never commit .env.
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m app.core.migrate
uvicorn app.api.main:app --host 127.0.0.1 --port 8000

# Separate shell: retain the existing VITE_API_URL configuration.
cd frontend
npm ci
npm run dev
```

For the existing Docker development setup, provision PostgreSQL/Redis first, then run
`docker compose run --rm --no-deps web python -m app.core.migrate` before starting the
upgraded web/worker services. Compose must supply the existing container database
hostname and persistent storage path. For the production image/release environment,
run `python -m app.core.migrate` with its existing credentials before API rollout, then
build/release the backend and `cd frontend && npm ci && npm run build` static assets.
These are instructions only: no deployment or image release was performed.

No new environment values or libraries. Production continues to require HTTPS,
`APP_ENV=production`, `SESSION_COOKIE_SECURE=true`, explicit origins and persistent
`STORAGE_DIR`. SameSite/cross-site limitations from Feature 4 still apply. New Chat's
retention increases storage usage; configure operational quotas/retention deliberately.

## Verification results

- Full backend regression suite: **153 passed**, including **9 real PostgreSQL checks**,
  no skips; two dependency deprecation warnings. History checks include migration
  repeatability, owned-title backfill, unchanged legacy quarantine, message pagination
  and concurrent save/deletion. [Saved results](verification/feature5-backend.txt).
- New authenticated history API coverage: **28 passed**, including anonymous/foreign
  CRUD rejection, forged fields, stable list and frozen message pagination, reopen
  memory continuity, deletion, failed file cleanup/retry, transaction rollback,
  ingestion deletion races and late audit privacy. Existing authentication expiration,
  CSRF and cross-user isolation regressions were included in the full suite.
- Frontend: **23 individual tests passed** (9 API/session and 14 workspace cases).
  `npm test` passed both test files. Cases include A → B → A stale answers, history
  races, deleted pending replies, older-page merging, scope restoration, user-specific
  ID preferences, reload fallback and late uploads/account deactivation.
- `npm run build`: passed (Vite production build).
- CI's fatal backend Flake8 check with `--jobs=1`: passed, **0 findings**. The sandbox
  blocks Flake8's multiprocessing IPC, so serial execution was used. The repository
  has no frontend lint script/configuration; frontend lint cannot be claimed passed.
  The existing nonblocking style/complexity check reports 17 findings (line length,
  indentation and complexity), including increased upload/startup complexity; it is
  not a clean full-style pass. [Lint output](verification/feature5-style-lint.txt).
- Browser smoke against a localhost-only real PostgreSQL API and mocked Gemini:
  login, empty state, automatic title, rename dialog/save, New Chat, reopening,
  follow-up memory, reload restoration, mobile drawer/Escape and deletion confirmation
  with Cancel passed. [Desktop evidence](verification/feature5-desktop.jpg),
  [mobile evidence](verification/feature5-mobile.jpg). Physical deletion is covered by
  automated tests. These screenshots show synthetic content, not a live Gemini result.

```bash
# From the repository root with development test dependencies installed:
pip install pytest httpx flake8
python -m pytest tests/ -q
flake8 app --jobs=1 --count --select=E9,F63,F7,F82 --show-source --statistics
(cd frontend && npm test && npm run build)

# Optional real PostgreSQL: use ONLY a disposable alex_memory_test* database.
# Set MEMORY_TEST_DATABASE_URL securely in the shell; never use application data.
python -m pytest tests/test_memory_postgres.py tests/test_auth_postgres.py tests/test_history_postgres.py -q
```

Real PostgreSQL verification used a temporary `pgvector/pgvector:pg16` container with
an isolated test database and test-only schemas. The temporary container, browser tab
and local test servers were removed/stopped after verification. Application data was not migrated.
Gemini was mocked; provider reliability/answer quality and production-scale query
latency were not measured. Existing embeddings tests used the locally cached model.

## Remaining limitations and next improvements

No cancellation/streaming or hybrid search is added. Switching chats doesn't cancel
server generation; guards protect the visible view and deletion rejects late storage.
Persistent local file cleanup has no scheduled worker yet; repeat DELETE is the retry
mechanism. Pre-increment unlinked audit text and backups need an operational retention
policy. Tombstones remain until an operator can safely define identifier-retention
rules. There is no cross-tab live push synchronization or conversation export/search.
Large-history performance has bounded queries and supporting indexes but no production
load benchmark. Add frontend lint tooling and CI checks in a separate reviewed change.
