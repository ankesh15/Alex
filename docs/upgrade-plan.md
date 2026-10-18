# ALEX upgrade plan and repository review

Current status: Features 1, 4 and 5 have been implemented and verified as separate
increments. See [the Feature 1 review](feature1-review.md), [authentication report](feature4-authentication.md)
and [persistent history report](feature5-history.md).
Remaining features are deferred; no commit or deployment has been performed.

Reviewed local `main` at `898aa29` before implementation. The working tree was clean.
Reviewed all tracked backend, frontend, test, configuration, and deployment files.

## Original architecture (before these increments)

React keeps messages only in component state and generates a new chat ID on reload.
General chat calls Gemini directly. Document chat executes a request-local LangGraph:
retrieve → relevance check → generation → citations, with a deterministic no-context
branch. FastEmbed produces 384-dimensional vectors. SQLAlchemy stores documents,
chunks, and audit logs in PostgreSQL/pgvector. SQLite tests use Python cosine search.
New Chat deletes the previous chat's documents. Celery/Redis are configured but the
upload endpoint performs extraction and embedding synchronously.

No authentication, user models, conversation tables, streaming, hybrid retrieval,
evaluation dataset, frontend lint configuration, or migration framework exists.
`BaseAgentState.messages` is unused by the RAG graph. Audit logs contain only a
truncated answer and do not constitute usable conversation memory.

## Findings, ordered by impact

- Critical: all document operations and paid Gemini calls are unauthenticated.
  A supplied chat ID is a filter, not proof of ownership. Omitting it searches or
  lists all documents; document detail/delete do not require it. CORS is not auth.
- High: durable transcripts need ownership and a retention/deletion policy before
  a public multi-user rollout. Do not expose history-list APIs until authentication.
- High: upload reads the whole payload before size rejection; parsing/embedding
  block an async endpoint. Only extensions are checked (README overstates MIME
  validation), parser errors are returned verbatim, and processing failure does not
  roll back before updating FAILED status. Move ingestion to existing workers.
- High: `_safe_file_path` checks a string prefix, allowing sibling directory names
  sharing the storage prefix; fix with resolved containment and regression tests.
- High: startup catches database errors and still reports healthy. Schema changes
  rely on create_all and an inline ALTER rather than versioned migrations.
- Medium: no vector index DDL exists despite README claims. PostgreSQL search can
  scan/sort all scoped chunks. Add measured index changes with hybrid retrieval.
- Medium: no pagination; duplicate ingestion stores extracted text and chunks;
  the embedding singleton has no initialization lock and each worker loads a model.
- Medium: only lower dependency bounds; CI uses plain PostgreSQL without pgvector,
  no frontend checks, and tests may download embeddings from external services.
- Medium: failed LLM responses use HTTP 200 and rely on a text prefix; client
  in-flight responses can append to a newly reset chat. Provider initialization was
  outside the existing error handler. No cancellation or request backpressure.
- Documentation: Dockerfile is single-stage; zero temperature does not guarantee
  faithfulness/determinism; citation lists represent retrieved sources, not verified
  support for every claim. No measured evaluation results are available.

## Reviewable increments

1. Feature 1: additive conversation/turn storage, bounded scope-specific history,
   LangGraph follow-up contextualization, general-chat memory, optimistic concurrency,
   frontend chat-ID propagation and stale-response guards, tests and migration.
2. Feature 4: users, password hashing, environment-backed secrets, secure sessions,
   login/signup/logout, mandatory ownership on documents/conversations/retrieval,
   rate limiting and authorization regression tests. Legacy anonymous records must
   not become claimable by knowledge of a chat ID. Preserve existing API components.
3. Feature 5: authenticated conversation CRUD, cursor pagination, responsive sidebar,
   reopening and explicit deletion/retention; change temporary-document lifecycle
   deliberately so old conversation citations remain usable.
4. Feature 2: shared generation service with SSE deltas, abort/disconnect handling,
   loading/error events, final citations, atomic persistence only on completion.
5. Feature 3: scoped PostgreSQL FTS + vector search, configurable RRF ranking,
   migration for indexes, relevance fixtures and query-plan/performance checks.
6. Feature 6: versioned evaluation dataset and reproducible offline/live runners for
   retrieval relevance, faithfulness, citation support and latency; publish measured
   baseline vs changed results. Never substitute mocked results for live metrics.

Each increment runs its targeted tests plus applicable regression, frontend, and
migration checks. Deployment files stay unchanged in Feature 1. Infrastructure and
credential limitations must be reported explicitly.

## Feature 1 decisions

- Existing `chat_id` is the conversation identifier. Omission preserves stateless
  legacy API behavior, including general chat without a database query.
- Store each completed user/assistant exchange atomically as a turn with citations,
  token usage, scope and status. A conversation revision gives deterministic ordering
  and detects concurrent requests from the same history snapshot (HTTP 409).
- General, all-documents, and each specific document have separate memory scopes.
  This intentionally sacrifices memory across scope changes to avoid feeding another
  document's answers into a narrower scope. No process-global history/checkpointer.
- Load only recent successful turns by index, bounded by count and character budget.
  Keep complete pairs, trim an oversized latest pair, and keep full stored text.
  Character limits are deterministic bounds, not claimed exact token counts.
- Add a contextualization node to the existing graph. It uses structured messages
  to rewrite follow-ups before embedding; rewrite failure falls back to the original
  question. History resolves references but is never document evidence. Citations
  come only from fresh, chat/document-filtered retrieval. Rewrite token usage counts
  toward reported totals.
- Failed/empty generations do not enter memory. No-context turns are stored for
  future history display but excluded from subsequent model context.
- Explicit SQL migration is additive, transactional and repeatable. Existing
  development create_all startup registers the new models; production operators
  should run the migration before deploying. No destructive rollback is supplied.
- No public history API or sidebar in this increment. PostgreSQL memory survives
  backend restarts for the same chat ID. Browser reload/reopening belongs to Feature
  5, after ownership checks. Existing temporary document cleanup remains in place.
- Chat IDs are not authentication. Feature 1 alone is not ready for public multi-user
  deployment. Ownership, transcript deletion and retention are next increments.

## Feature 5 decisions

The existing owned conversation/turn tables remain the source of truth. A thin CRUD
and paginated message view now support a responsive sidebar and reopening. New Chat
preserves prior attached documents. Confirmed deletion removes exchanges and document
content, retains a minimal tombstone to reject late writes, and supports file-cleanup
retry. Legacy NULL owners stay quarantined. See the history report for contracts,
race protections, migration and measured verification results. Features 2, 3 and 6
remain deferred.
