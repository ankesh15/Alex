# Feature 1 review before authentication

Reviewed the complete uncommitted Feature 1 implementation, its API/frontend wiring,
models, migration and tests before starting Feature 4. A source snapshot excluding
secrets/dependencies was saved under `/tmp/alex-feature1-review-01a13471`.

## Correctness and regressions

History is indexed and bounded, chronological, scoped by chat and document selection,
and restricted to successful turns. Oversized latest exchanges retain both message
roles. Completed turns and revisions commit atomically; optimistic concurrency
rejects stale answers. Rewrite token usage is included, rewrite failures fall back,
and no retrieved context still prevents synthesis. Citations use fresh chunks.
Frontend guards prevent delayed responses from updating a new chat. No destructive
schema change or replacement of working retrieval/generation components was found.

## Findings resolved by Feature 4

- Critical: conversation IDs alone permit memory access. Document list/detail/delete
  and retrieval lack user ownership, and unscoped queries disclose other data.
  Require authenticated sessions and server-derived ownership throughout API/services.
- High: old ownerless transcripts/documents cannot safely be assigned to the first
  person presenting an ID. Quarantine NULL ownership, never automatically claim it.
- Medium: retrieval leaves a read transaction open while generation waits on Gemini.
  Release that read transaction once retrieved dictionaries have been materialized.
- Medium: storage exceptions need consistent sanitized responses across protected
  endpoints, rather than exposing database/parser details.

## Remaining deliberate limits

Scope changes keep separate windows. Browser reopening, history management UI,
storage retention and summarization are not added in this authentication increment.
The current New Chat document cleanup can leave historical citation references to
deleted files. Failed Gemini calls retain the existing HTTP-200 answer contract.
Live model rewrite accuracy/faithfulness remains unmeasured.

Review baseline: 81 tests passed and 3 optional PostgreSQL tests skipped before changes.
The initial permission review timed out; one authorized retry completed successfully.
Final authenticated regressions and PostgreSQL results are in the Feature 4 report.
