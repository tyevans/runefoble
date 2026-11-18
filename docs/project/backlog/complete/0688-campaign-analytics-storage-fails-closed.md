---
id: '0688'
title: Campaign Analytics Storage Fails Closed When PostgreSQL Is Unreachable
status: Complete
created: 2026-11-17
dependencies:
- TASK-0684
- TASK-0573
governing_adrs:
- ADR-0015
- ADR-0011
governing_prds:
- PRD-0012
governing_stories:
- US-0040
target_release: 0.9.0
---

# TASK-0688: Campaign Analytics Storage Fails Closed When PostgreSQL Is Unreachable

## Status
Complete

## Summary
`campaign_analytics` catches any failure to connect to PostgreSQL at start-up and switches to an in-memory store. A deployed service then accepts writes and loses them on restart. The bus factory in the same service also suppresses every error. This task makes start-up fail when the database is configured and unreachable, and removes the silent fallback.

## Problem Statement
- `services/campaign_analytics/src/campaign_analytics/storage.py:52-58`: `create_async_engine` and `create_all` are wrapped in `except Exception` that logs "Using in-memory fallback" and returns an in-memory store.
- `services/campaign_analytics/src/campaign_analytics/dependencies.py:60-66`: `get_event_bus` wraps the Redis bus creation in `contextlib.suppress(Exception)`.
- TASK-0573 moves the query state to durable storage. Both tasks touch `storage.py`. Sequence 0573 first, or rebase this work on it.

## Documentation & Architecture Review
- ADR-0015 (f): deployed services fail fast when the store is not configured. The in-memory store is for tests only.
- ADR-0011: event store and read model access through the approved repository.
- `docs/how-to/project-campaign-analytics-and-chronicle-timeline.md`: state the start-up failure.

## Product & User Story References
- PRD-0012 and US-0040 (combat telemetry and chronicle timeline). Data loss is a user-visible defect.

## Detailed Specification & Implementation Plan
1. Remove the `except` fallback in `storage.py`. A failed connect or table creation raises at start-up. Keep an in-memory store only in test fixtures that pass it explicitly.
2. Use the shared bus factory from TASK-0684. Delete the `contextlib.suppress` in `dependencies.py`.
3. Add a lifespan check that opens the connection before the service reports ready.
4. Update the test fixtures to use the PostgreSQL container when available (existing `postgres_service` fixture pattern).

## Frontdoor Blackbox Test Plan
- Start the service with a PostgreSQL URL on a closed port. Start-up fails with a clear error. No request is served.
- Start the service with a PostgreSQL container. Post a telemetry event through the public route, restart the service, and read the projection through the public query route. The value is still there (durable).
- Start the service with the Redis URL on a closed port. Start-up fails.

## Definition of Done
- No silent fallback in `campaign_analytics` production code.
- `uv run pytest` and `make lint` pass. Docker is needed for the container tests.
- Reference doc states the start-up failure mode.

## Audit Provenance

- Severity: high
- Source audits: `work/0578.md`
