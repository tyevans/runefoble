---
id: '0782'
title: Test Containers Fail Loudly and Redis Test Containers Carry Owner Labels
status: Refined
created: 2026-11-17
dependencies: []
governing_adrs:
- ADR-0005
- ADR-0014
governing_prds: []
governing_stories: []
target_bc: tests
target_release: 0.9.0
---

# TASK-0782: Test Containers Fail Loudly and Redis Test Containers Carry Owner Labels

## Status
Refined. Found during batch 23 integration, 2026-11-17.

## Summary
The PostgreSQL fixture catches `Exception` and yields `None`, so a broken Docker setup skips tests in silence. It also never removes its temp file. The Redis test container leaks when a run is killed, in the same way the PostgreSQL containers did before TASK-0777.

## Problem Statement
- `tests/helpers/postgres.py` (or the `postgres_service` fixture in `tests/conftest.py`): `except Exception: yield None`, and a temp file that is not removed.
- The Redis container helper starts containers with no `runefoble.test.owner-pid` and `runefoble.test.owner-host` labels.

## Documentation & Architecture Review
- AGENTS.md hard invariants and DoR 9 (no compatibility shims).
- ADR-0005, ADR-0014.

## Product & User Story References
None. Platform quality work.

## Detailed Specification & Implementation Plan
1. Catch only the Docker-unavailable error and skip with a reason. Any other error fails the test.
2. Remove the temp file in the fixture teardown.
3. Give Redis test containers the same owner labels, and remove orphans with the helpers in `tests/helpers/container_owner.py`.

## Frontdoor Blackbox Test Plan
- A fixture failure that is not "Docker unavailable" fails the test with the error.
- After a run, no temp file from the fixture stays on disk.
- A Redis container whose owner process is dead is removed at the next session start.

## Definition of Done
- The test plan passes.
- `uv run pytest`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: medium
- Source audits: `.audit/work/0777.md` (Discovered)
