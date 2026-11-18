---
id: '0708'
title: Audience Studio Appends Events Before It Publishes and Maps Version Conflicts
status: Complete
created: 2026-11-17
dependencies: []
governing_adrs:
- ADR-0011
- ADR-0015
governing_prds:
- PRD-0011
governing_stories: []
target_bc: audience_studio
target_release: 0.9.0
---
# TASK-0708: Audience Studio Appends Events Before It Publishes and Maps Version Conflicts

## Status
Complete

## Summary
The audience commit path publishes events to Redis Streams before it appends them to the store. A failed append leaves published events for a rejected command. A concurrent write hits a PostgreSQL primary-key error that the service returns as a raw 500.

## Problem Statement
- `services/audience_studio/src/eventSourcing/repository.ts:74-96`: the publish loop runs before `this.store.appendAll(changes)`. The header comment accepts publish failure only, not append failure.
- `services/audience_studio/src/eventStore/postgresEventStore.ts:126-144`: the version check reads `MAX(version)` without a lock. A losing writer hits the `(stream_id, version)` key. Error code `23505` has no mapping (no reference to it in `src`), so the client gets a 500.
- `services/audience_studio/src/errors.ts` has no 409 status.
- `keyedMutex.ts` is per process. The chart allows more than one replica.

## Documentation & Architecture Review
- AGENTS.md hard invariants and DoR 9 (no compatibility shims).
- ADR-0011, ADR-0015.
- `docs/how-to/` and `docs/reference/` pages named in the specification.

## Product & User Story References
- PRD-0011

## Detailed Specification & Implementation Plan
1. Write events and one outbox row per event in the same transaction as `appendAll`.
2. Add an outbox relay module that publishes pending rows to `AUDIENCE_STREAM` after commit and marks them sent. Event ids stay derived from stream and version, so a retry is idempotent.
3. Map PostgreSQL `23505` on the version key to `ConcurrencyConflictError` in `PostgresEventStore`.
4. Add a 409 `HttpError` subclass and return it from the route layer for `ConcurrencyConflictError`.
5. Remove the publish-before-append loop from `repository.ts`. Keep the Redis ping guard only if the relay needs it.
6. Document the outbox in `docs/reference/events-schema.md`.

## Frontdoor Blackbox Test Plan
- Fail the publisher after a successful append (through the injected fake). No stream event exists without a stored event. The relay publishes it on retry.
- Two concurrent votes on the same poll over HTTP: one returns 2xx, the other returns 409. Neither returns 500.
- Existing `test/event_store.test.ts` and `test/poll_http.test.ts` pass.

## Definition of Done
- The specification steps are done and the tests above pass.
- Docs named in the specification are corrected.
- `uv run pytest`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: high
- Source audits: `refactor-r1/audience-scripts-helm.md`
