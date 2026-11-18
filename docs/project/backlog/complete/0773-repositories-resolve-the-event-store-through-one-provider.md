---
id: '0773'
title: Repositories Resolve the Event Store Through One Provider
status: Complete
created: 2026-11-17
dependencies:
- TASK-0707
- TASK-0769
governing_adrs:
- ADR-0011
- ADR-0015
governing_prds: []
governing_stories: []
target_bc: core
target_release: 0.9.0
---

# TASK-0773: Repositories Resolve the Event Store Through One Provider

## Status
Complete

## Summary
Module-level aggregate repositories capture the event store at import time. Fixtures that replace the store later leave those repositories on the old store, so tests patch a store the route does not use.

## Problem Statement
- `libs/runefoble_platform/src/runefoble_platform/event_sourcing.py:138-149`: `create_aggregate_repository` reads `get_event_store()` once.
- Service modules create repositories at import (for example `character_sheet.dependencies.repo`).
- Batch 18 had two order-dependent crafting failures from this.

## Documentation & Architecture Review
- AGENTS.md hard invariants and DoR 9 (no compatibility shims).
- ADR-0011, ADR-0015.

## Product & User Story References
None. Platform quality work.

## Detailed Specification & Implementation Plan
1. Add an `EventStoreProvider` like `EventBusProvider` (TASK-0684): lazy construction from settings, `get()`, `set()`, fail-fast connect for lifespans.
2. Repositories take the provider and resolve the store per operation, or services build repositories in their lifespan from the provider. Choose one and apply it to every service. No module-level store capture.
3. The test harness (TASK-0697/0769) owns one store seam that restores after each test.

## Frontdoor Blackbox Test Plan
- Replace the store through the harness seam. Write through a public route. Read through a public route. Assert the read sees the write (same store).
- Store outage through the harness seam: every service route answers 503.

## Definition of Done
- No repository keeps a store from import time.
- `uv run pytest`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: medium
- Source audits: `work/batch18b.gates.log`
