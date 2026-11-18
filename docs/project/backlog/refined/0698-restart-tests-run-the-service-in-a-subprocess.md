---
id: '0698'
title: Restart Tests Run the Service in a Subprocess Over a Shared Event Store
status: Refined
created: 2026-11-17
dependencies:
- TASK-0697
governing_adrs:
- ADR-0011
- ADR-0014
governing_prds: []
governing_stories: []
target_bc: core
target_release: 0.9.0
---
# TASK-0698: Restart Tests Run the Service in a Subprocess Over a Shared Event Store

## Status
Refined. Agreed at the refactor pause on 2026-11-17 (candidate 2).

## Summary
Restart tests (TASK-0567, TASK-0566) simulate a restart by re-importing service modules in the test process. This is fragile and can break other tests that hold module references.

## Problem Statement
- TASK-0567 restart tests re-import `game_session` with fresh module state.
- TASK-0566 checks only that the event store keeps state.

## Documentation & Architecture Review
- AGENTS.md hard invariants and DoR 9 (no compatibility shims).
- ADR-0011, ADR-0014.

## Product & User Story References
None. Platform quality work.

## Detailed Specification & Implementation Plan
1. Add a `serve_subprocess(app_path, env)` helper to `tests/helpers/live_services.py` that starts a service with uvicorn in a child process on a loopback port.
2. Share the event store between restarts with the PostgreSQL test container (`tests/helpers/postgres.py`), marked `docker`.
3. Move the TASK-0566 and TASK-0567 restart tests (and the TASK-0702 voice room test) to it. Delete the re-import code.

## Frontdoor Blackbox Test Plan
- Each restart test: write through the public route, stop the child process, start a new one, read through the public route.
- Prove each test fails on the old in-memory code (record before and after in the report).

## Definition of Done
- No test re-imports service modules to simulate a restart.
- `uv run pytest`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: medium
- Source audits: `work/0567.md`, `work/0566.md`
