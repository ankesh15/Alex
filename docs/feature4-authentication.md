# Feature 4: authentication and authorization

> Historical increment report: Feature 5 now supplies history management and changes New Chat to retain earlier documents. See [the current history report](feature5-history.md).

## Scope and Feature 1 review

The [Feature 1 review](feature1-review.md) preceded implementation. Its baseline was
81 passing tests, with 3 optional PostgreSQL tests skipped. Memory truncation,
scope isolation, atomic exchanges, conflict detection and fresh citation generation
were correct. The main security gap was missing user ownership; retrieval also held
a read connection during Gemini generation. This increment resolves both.

No streaming, hybrid search, evaluation runner, conversation CRUD, sidebar, browser
conversation reopening, or other feature was started. A minimal authorized transcript
read endpoint supports access checks; there is no new history management UI.
Nothing was committed, pushed or deployed. All changes are available for approval.

## Architecture

Before: public chat/document endpoints and nullable chat filters; conversation IDs
could reveal memory and document IDs could read/delete arbitrary records.

After: users, revocable cookie sessions and shared authentication throttles live in
the existing PostgreSQL/SQLAlchemy infrastructure. A shared FastAPI dependency
authenticates the cookie, checks active user/expiration/revocation, validates CSRF
for mutations and supplies a server-derived principal. Protected router defaults
cover all chat and document operations, including any future route added to them.
No streaming endpoint exists in this increment.
Any later streaming handler must also use the authenticated principal and ownership
helpers before loading its conversation/documents; router authentication alone is
not a substitute for its resource authorization.

Every new persisted conversation, exchange, document and RAG audit gets that owner's
ID. Chunks inherit ownership through their document. Service-level memory/retrieval
filters also enforce ownership. PostgreSQL composite foreign keys prohibit messages
and documents from referring to a conversation with a different non-NULL owner.
NULL ownership exists only for quarantined legacy rows, excluded from all user reads.

The React application remains a tabbed SPA. A protected gate wraps both Chat and
Documents without adding a routing dependency or replacing their design. Session
restoration precedes rendering; logout/401 unmount the entire workspace. Signup,
login, confirmation, loading and error states have labels and native keyboard forms.
The header shows the account and logout; small-screen navigation remains compact.

## Password and session protections

- Salted scrypt uses Python's standard library, N=131072, r=8, p=1, a random 16-byte
  salt and 32-byte derived key. This matches [OWASP's scrypt guidance](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html).
  Signup passwords are 12–128 characters, accept Unicode, and are never trimmed.
  Constant-time verification and dummy-account hashing reduce login account leaks.
  Hash parsing caps parameters rather than trusting arbitrary work factors.
- A per-process two-slot hash semaphore limits concurrent memory consumption;
  saturated hashing returns a retryable 503. Authentication attempts use a shared
  database fixed-window counter, default 20 requests per peer IP per 300 seconds.
  Signup and login share that counter. Concurrent PostgreSQL workers increment it
  atomically. Application code never trusts an `X-Forwarded-For` value itself.
- Session tokens are independent random 256-bit values. Only SHA-256 digests are
  stored; no bearer token is returned in JSON, logged, or stored in browser storage.
  Password hashes and session digests are distinct mechanisms. No JWT/signing-secret
  dependency is needed. Database and Gemini credentials remain environment-managed.
- Cookies are HttpOnly, host-only, path `/`, and use configurable SameSite. Secure
  mode names the cookie `__Host-alex_session` to prevent Domain-cookie injection.
  Production and SameSite=None reject insecure configuration. Login/signup issue a
  fresh token and revoke the prior cookie session; logout revokes the current session.
  Multiple devices may retain independent sessions.
- Absolute expiry defaults to 7 days; idle expiry defaults to 12 hours. Each authorized
  request updates last-seen time without holding the connection during generation.
  Disabled users, expired or revoked sessions return 401.
- Mutations require an `X-CSRF-Token` matching the session's random token. `/auth/me`
  restores it into frontend memory. All API fetches include credentials. Origin
  checks cover protected mutations and login/signup, and wildcard CORS is rejected.
  Third-party origins cannot read session/CSRF responses through CORS.
- Validation errors do not echo submitted passwords or private questions. API
  responses use no-store caching, and database errors return sanitized 503 messages.
  Session design follows [OWASP session management](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html)
  and [CSRF guidance](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html).

## Authorization and preserved memory

Client IDs are selectors, never credentials. An unknown chat ID may create a new
conversation owned by the authenticated requester; an existing foreign or unowned
ID returns 404. It can never be claimed by presenting the identifier. Chat JSON
rejects extra `user_id` fields; an upload's forged owner form field is ignored and the
real owner is assigned server-side. A guessed document ID is checked before Gemini
or application file access. Missing chat filters still restrict queries to that user.

The original General/All Documents/specific-document memory windows, history bounds,
rewrite failure fallback, citations, token accounting and revision conflict handling
remain. Memory snapshots and conditional writes now carry the authenticated owner.
The graph releases its retrieval read transaction before generation. Authenticated
requests without chat IDs remain stateless for memory, while authentication still
uses the database. Existing temporary-document cleanup on New Chat remains owner-only.
Late responses cannot populate a logged-out or newly authenticated workspace.

Document authorization also fixes sibling-prefix/symlink storage-path escapes,
limits file reads to the configured cap plus one byte, sanitizes processing errors,
and rolls back before marking a failed ingestion. Full MIME/signature/archive-bomb
validation and asynchronous ingestion remain future hardening.

## API contract

| Operation | Access |
| --- | --- |
| POST `/api/v1/auth/signup` | Email/password JSON; trusted browser Origin; rate-limited; creates session |
| POST `/api/v1/auth/login` | Email/password JSON; trusted browser Origin; rate-limited; rotates session |
| GET `/api/v1/auth/me` | Valid cookie; returns user, CSRF token, absolute expiry |
| POST `/api/v1/auth/logout` | Valid cookie + CSRF; revokes and clears cookie |
| All `/api/v1/documents` operations | Valid cookie; mutations additionally require CSRF; owner checks |
| POST `/api/v1/chat`, `/chat/general` | Valid cookie + CSRF; owner-scoped memory and retrieval |
| GET `/api/v1/chat/{chat_id}/history` | Valid cookie + ownership; optional `limit` 1–100 and `before_turn` |
| `/`, `/health`, OpenAPI docs | Public; no user data |

Signup/login/me return `{user: {id, email}, csrf_token, expires_at}`. Send cookies and
`X-CSRF-Token` for protected POST/DELETE requests; no API trusts a user ID supplied by
the client. HTTP 401 means reauthenticate, 403 means CSRF/origin rejection, 404 means
unavailable resource, 409 means duplicate signup or memory conflict, 429 means auth
throttling and 503 means storage/hash capacity is unavailable. Provider errors retain
the existing chat answer contract to avoid expanding this increment into generation
API redesign.

## Safe migration and unowned-data strategy

`python -m app.core.migrate` applies the original additive memory DDL and
`migrations/002_user_auth.sql`. The latter transaction creates users, sessions and
throttles, adds nullable owner FKs/indexes, and installs composite ownership constraints.
It never deletes, truncates, reassigns, or guesses ownership of legacy data. Re-running
it is supported. The original memory migration commits separately; if auth migration
fails, resolve the failure before starting the backend. Startup rejects absent owner
columns/constraints and database initialization failures.

Existing ownerless conversations, messages, documents and audits retain all content
and remain inaccessible to ordinary accounts. There is no claim API, automatic
assignment to the first signup, or migration based on a supplied chat ID/email. Keep
the original database and storage backup. For recovery, an administrator must verify
ownership out of band, review a specific mapping, and migrate all related records
consistently in a separate approved operation or export/import verified content.
No administrative reassignment tool or reassignment was performed here.

SQLite tests support additive owner columns without rebuilding old tables. SQLite
cannot add composite FKs to existing tables without a rebuild; the test helper does
not perform one. Fresh SQLite fixtures enforce them from ORM definitions. Production
is PostgreSQL, and actual PostgreSQL upgrade/constraint checks passed.

## Install, run, verify and deploy after approval

No new runtime or frontend dependencies were added. Existing Python requirements and
Node packages suffice; scrypt needs the normal Python/OpenSSL build.

```bash
cd /home/ankesh/ALEX/Alex
source venv/bin/activate
pip install -r requirements.txt
pip install pytest flake8
# Add the new auth settings from .env.example to your existing .env.
# Preserve existing keys. Local HTTP needs SESSION_COOKIE_SECURE=false.
docker compose up -d postgres
python -m app.core.migrate
uvicorn app.api.main:app --host 0.0.0.0 --port 8000 --reload
```

Frontend, in another terminal:

```bash
cd /home/ankesh/ALEX/Alex/frontend
npm install
npm run dev
```

Use one hostname consistently (`localhost` or `127.0.0.1`). Existing local Vite `/api`
proxy is supported. Test credentials must be your own local accounts; synthetic test
passwords in automated fixtures are not deployment credentials.

```bash
cd /home/ankesh/ALEX/Alex
source venv/bin/activate
pytest tests/ -q
pytest tests/test_auth.py tests/test_conversation_memory.py -v
flake8 app tests --jobs=1 --select=E9,F63,F7,F82 --show-source --statistics
cd frontend
npm test
npm run build
```

Optional PostgreSQL tests require `MEMORY_TEST_DATABASE_URL` supplied through your
environment, pointing only to a disposable database named `alex_memory_test*`:

```bash
pytest tests/test_memory_postgres.py tests/test_auth_postgres.py -v
```

**Deployment is pending your approval.** After approval, back up PostgreSQL and file
storage, take the old unauthenticated backend offline, and configure:

- `APP_ENV=production`, `SESSION_COOKIE_SECURE=true`, and HTTPS.
- Explicit `ALLOWED_ORIGINS`/`FRONTEND_URL`; the wildcard is no longer valid.
- `SESSION_COOKIE_SAMESITE=lax` for same-site deployments. Different Vercel/Railway
  sites require `none` plus Secure cookies; browsers can block third-party cookies.
  Prefer same-site custom domains or a same-origin proxy. No deployment rewrite was
  silently introduced.
- Existing production `DATABASE_URL`, `GOOGLE_API_KEY`, storage volume and frontend
  `VITE_API_URL`. Do not use development database credentials in production.
- A controlled trusted-proxy policy: configure Uvicorn forwarding trust only for your
  actual proxy network so a client cannot spoof the resolved IP. Behind an untrusted
  shared proxy, the app may throttle multiple people as one peer; adjust deliberately.

For an existing Compose deployment, after approval and with appropriate secrets:

```bash
docker compose stop web
docker compose build web
docker compose run --rm --no-deps web python -m app.core.migrate
docker compose up -d web
```

Inside Compose, the database host is `postgres`; a host-side CLI uses a host-accessible
URL. On Railway, run the migration through your release/service shell before starting
the new version. Build and release the frontend through the existing Vercel process.
Verify signup/login, protected document operations, logout and an expired session
before restoring traffic. Do not run old unauthenticated binaries alongside the new
schema. A schema rollback does not make old unauthenticated access safe.

Dockerfile, Compose, Railway and Vercel deployment configuration files were unchanged.
Only the documented environment/migration/startup requirements changed.

## Verification

Verified October 13, 2026 with the existing Python 3.14.4 environment and Node 22.22.1.

| Check | Result |
| --- | --- |
| Pre-auth Feature 1 review baseline | 81 passed, 3 optional PostgreSQL checks skipped |
| Final complete backend suite, PostgreSQL enabled | 122 passed; no skips |
| Included real PostgreSQL migration/security/memory checks | 6 passed |
| Frontend API/session tests | 8 passed |
| Frontend production build | Passed |
| Python CI fatal-error lint selection and whitespace check | Passed |
| Browser signup/login/logout | Passed with synthetic accounts in disposable PostgreSQL |
| Browser cookie restoration and authenticated follow-up memory | Passed using a deterministic mock model |
| Logout during in-flight answer, then another signup | New protected workspace did not display the old answer |
| Frontend lint | Not configured in the existing repository; no lint pass claimed |
| Live Gemini quality/evaluation or live deployment | Not performed |

Real auth tests never override the authentication dependency. Existing pipeline tests
explicitly inject a fixed principal to keep unit tests focused, and seed owned data;
their auth requirements were updated rather than dropping assertions. Real-auth
SQLite fixtures enable foreign keys. PostgreSQL checks use isolated disposable schemas
and verify old documents, messages and audits are preserved/unowned, repeated upgrade
is safe, wrong-owner relationships are rejected, and shared rate counters are atomic.
The temporary database and browser smoke servers are stopped after verification.

![Authenticated follow-up memory with a mock model](verification/auth-memory.jpg)
![Login gate after logout](verification/auth-login.jpg)

## Known limitations

Email verification, password reset, MFA/passkeys, account deletion, session-management
UI and expired-session/rate-row cleanup are not implemented. Signup duplicate status
can reveal that an email is already reserved. IP throttling does not replace edge
abuse protection, distributed attack detection or per-user AI quotas. Scrypt uses
about 128 MiB per hash; the two-slot limit is per worker, so size worker counts and
memory accordingly. Session revocation prevents later requests; a request authorized
before logout may complete on the server, while the frontend discards its response.

HTTPS and production proxy/origin configuration must be validated in your deployment.
Cookie browser policies can block cross-site setups. This is a tested authentication
increment, not a certification of the whole application's production security.
Conversation reopening/CRUD/sidebar, history deletion/retention, document ingestion
hardening and provider error redesign remain deferred. New Chat still deletes old
documents and can leave historical citations pointing to removed files. No streaming
or hybrid search was added. Live Gemini/RAG evaluation remains unmeasured.

## Reviewable files

The [complete Feature 4 file manifest](feature4-files.md) and an
[authentication-only patch](feature4-auth-only.patch) against the saved Feature 1
snapshot are provided with this report. Feature 1 is uncommitted, so
the normal Git diff against `898aa29` also includes that earlier increment. The patch
does not include binary verification screenshots; those are linked above. No secret
environment file or the unrelated untracked `:memory:.ses` artifact is included.
