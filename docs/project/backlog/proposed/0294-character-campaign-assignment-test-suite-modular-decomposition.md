---
id: '0294'
title: Character Campaign Assignment Test Suite Modular Decomposition
status: Proposed
created: 2026-09-28
dependencies:
- TASK-0253
governing_adrs:
- ADR-0001
- ADR-0002
- ADR-0007
- ADR-0013
governing_prds:
- PRD-0006
- PRD-0023
governing_stories:
- US-0064
target_release: 0.8.0
---

# TASK-0294: Character Campaign Assignment Test Suite Modular Decomposition

## Status
Proposed

## Summary
Decompose `tests/test_blackbox_character_campaign_assignment.py` (295 lines, 59.0% of limit) into modular test submodules under `tests/test_blackbox_character_campaign_assignment/` (`conftest.py`, `test_assignment_events.py`, `test_assignment_api.py`, `test_aggregate_state.py`), ensuring all test files remain strictly < 110 lines per Hard Invariant 6.

## Problem Statement
`tests/test_blackbox_character_campaign_assignment.py` verifies CloudEvents schemas, event serialization round-trips, character sheet aggregate assignment state transitions, REST endpoints, and SpiceDB Zanzibar permission checks in a single 295-line module. As multiclassing, level milestones, and secondary campaign party transfers are incorporated, this file will rapidly approach the 500-line invariant limit unless decomposed into focused, single-responsibility submodules.

## Governing Architecture & ADRs
- **ADR-0001: SpiceDB Zanzibar Object Authorization**: Validates fine-grained membership and DM assignment checks.
- **ADR-0002: Domain Events via eventsource-py**: Validates `CharacterAssignedToCampaign` and `CharacterUnassignedFromCampaign` events.
- **ADR-0007: Domain-Driven Design Architecture**: Clean domain model and aggregate state transitions.
- **ADR-0013: Modular Decomposition**: All source files kept strictly < 500 lines (submodules < 110 lines).

## Scope of Work
1. **Shared Fixtures (`tests/test_blackbox_character_campaign_assignment/conftest.py`)**:
   - Extract mock SpiceDB clients, FastAPI TestClient instances, and test IDs (< 50 lines).
2. **Event Schema & Registry Tests (`tests/test_blackbox_character_campaign_assignment/test_assignment_events.py`)**:
   - Extract `CharacterAssignedToCampaign` registry resolution, CloudEvents attributes, and payload serialization (< 90 lines).
3. **Aggregate State Transition Tests (`tests/test_blackbox_character_campaign_assignment/test_aggregate_state.py`)**:
   - Extract `assign_to_campaign()` mutations, unassignment, and duplicate prevention tests (< 90 lines).
4. **REST API & Zanzibar Authorization Tests (`tests/test_blackbox_character_campaign_assignment/test_assignment_api.py`)**:
   - Extract campaign assignment endpoints, unassignment endpoints, and SpiceDB permission enforcement (< 100 lines).
5. **Verification**:
   - Safely remove monolithic `tests/test_blackbox_character_campaign_assignment.py` and run `uv run pytest tests/test_blackbox_character_campaign_assignment/`.

## Definition of Done
- `tests/test_blackbox_character_campaign_assignment.py` decomposed into `tests/test_blackbox_character_campaign_assignment/` suite.
- All extracted test files strictly < 110 lines per Hard Invariant 6.
- 100% test passing via `uv run pytest tests/test_blackbox_character_campaign_assignment/`.
- Monolithic `tests/test_blackbox_character_campaign_assignment.py` safely removed.
