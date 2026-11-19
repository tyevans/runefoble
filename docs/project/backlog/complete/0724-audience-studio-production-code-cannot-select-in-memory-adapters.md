---
id: '0724'
title: Audience Studio Production Code Cannot Select In-Memory Adapters
status: Complete
created: 2026-11-17
dependencies:
- TASK-0499
governing_adrs:
- ADR-0015
governing_prds:
- PRD-0011
governing_stories: []
target_bc: audience_studio
target_release: 0.9.0
---
# TASK-0724: Audience Studio Production Code Cannot Select In-Memory Adapters

## Status
Complete

## Summary
`NODE_ENV=test` selects in-memory stores in the production bundle. ADR-0015 (f) says production code must not select memory. The routes file also repeats eight try/catch blocks.

## Problem Statement
- `services/audience_studio/src/adapters.ts:25,51,137-161`: `MemoryEventStore` and `InMemoryStreamPublisher` (`src/memoryStreams.ts`) are chosen when `NODE_ENV === 'test'`. `mock://` Redis URLs are allowed under the same flag.
- `src/index.ts:21` passes `createAdapters` into `buildServer`, which accepts an injected factory (`server.ts:200`).
- `services/audience_studio/src/eventStore/types.ts:33`: `EventStore.kind` has no reader.
- `services/audience_studio/src/routes.ts:61-198`: eight identical try/catch blocks that call `sendError`. `createAudienceRoutes` is about 175 lines.

## Documentation & Architecture Review
- AGENTS.md hard invariants and DoR 9 (no compatibility shims).
- ADR-0015.
- `docs/how-to/` and `docs/reference/` pages named in the specification.

## Product & User Story References
- PRD-0011

## Detailed Specification & Implementation Plan
1. Move the memory store and the mock publisher to `test/fakes/`. `index.ts` builds PostgreSQL and Redis adapters only and fails at start-up when `DATABASE_URL` or `REDIS_URL` is missing. Tests inject fakes through `createAdapters`.
2. Delete the `NODE_ENV` branches and `EventStore.kind`.
3. Add one `setErrorHandler` for `HttpError`. Remove the try/catch blocks and `sendError`. Split routes into `routes/polls.ts` and `routes/proposals.ts`. Error bodies and statuses stay the same.
4. Sequence after TASK-0499, which edits the same files.

## Frontdoor Blackbox Test Plan
- `test/config.test.ts`: start-up refuses without `DATABASE_URL` or `REDIS_URL` for any `NODE_ENV`.
- `test/poll_http.test.ts` and `test/authorization_http.test.ts` pass with unchanged 403, 404 and 503 bodies.

## Definition of Done
- The specification steps are done and the tests above pass.
- Docs named in the specification are corrected.
- `uv run pytest`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: low
- Source audits: `refactor-r1/audience-scripts-helm.md`
