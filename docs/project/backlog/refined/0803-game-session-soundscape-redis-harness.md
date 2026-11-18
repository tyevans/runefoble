---
id: '0803'
title: "One Test Harness Runs Game Session, Redis and Soundscape Together"
status: Refined
created: 2026-11-18
dependencies: []
governing_adrs:
- ADR-0007
- ADR-0014
governing_prds: []
governing_stories: []
target_bc: tests
target_release: 0.9.0
---

# TASK-0803: One Test Harness Runs Game Session, Redis and Soundscape Together

## Status
Refined. Found during batch 26 to 28 integration, 2026-11-18.

## Summary
No test runs game_session and soundscape against one Redis, so the combat-end event path (TASK-0792) is tested only in parts.

## Problem Statement
- TASK-0792: `POST /api/v1/sessions/{id}/combat/end` emits `CombatEncounterEnded`. Soundscape consumes it. No test crosses the real Redis stream between the two services.

## Documentation & Architecture Review
- AGENTS.md hard invariants and DoR 9 (no compatibility shims).
- ADR-0007, ADR-0014.

## Product & User Story References
None. Platform quality work.

## Detailed Specification & Implementation Plan
1. Extend `tests/helpers/live_services.py` (or `service_harness.py`) with a harness that starts game_session and soundscape as processes with one Redis container.
2. Add a frontdoor test: end combat through the game_session route, then read the soundscape public state and see the combat-end change.

## Frontdoor Blackbox Test Plan
- The new test passes and stops all processes and the container when it ends.

## Definition of Done
- The test plan passes.
- `make test`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: medium
- Source audits: `.audit/drafts/round3-notes.md` batch 26 (Discovered)
