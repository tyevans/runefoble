---
id: '0317'
title: Microfrontend Manifests Test Suite Modular Decomposition
status: Proposed
created: 2026-09-28
dependencies:
- TASK-0026
- TASK-0088
governing_adrs:
- ADR-0004
- ADR-0013
governing_prds: []
governing_stories: []
target_release: 0.8.0
---

# TASK-0317: Microfrontend Manifests Test Suite Modular Decomposition

## Status
Proposed

## Summary
Decompose `tests/test_microfrontend_manifests.py` (289 lines, 57.8% of limit) into modular test sub-suites under `tests/test_microfrontend_manifests/` (`conftest.py`, `test_core_manifests.py`, `test_extended_manifests.py`, `test_manifest_schema_invariants.py`), keeping each test module strictly < 110 lines per Hard Invariant 6.

## Problem Statement
`tests/test_microfrontend_manifests.py` validates microfrontend UI manifests and component contracts across all service bounded contexts (game_session, board_state, character_sheet, the_watcher, voice_agent, campaign_lore, rules_compendium, asset_forge, soundscape, audience_studio). As additional service bounded contexts and microfrontends are integrated, this file will rapidly approach the 500-line ceiling unless organized into specialized sub-suites.

## Governing Architecture & ADRs
- **ADR-0004: Bauhaus Microfrontend Design System**: Component manifest contracts and packaging.
- **ADR-0013: Modular Decomposition**: All test files kept strictly < 500 lines (submodules < 110 lines).

## Scope of Work
1. **Fixtures & App Clients (`tests/test_microfrontend_manifests/conftest.py`)**:
   - TestClient fixtures for each bounded context service app (< 60 lines).
2. **Core Manifests Suite (`tests/test_microfrontend_manifests/test_core_manifests.py`)**:
   - Tests for board_state, character_sheet, game_session, the_watcher, voice_agent (< 95 lines).
3. **Extended Manifests Suite (`tests/test_microfrontend_manifests/test_extended_manifests.py`)**:
   - Tests for campaign_analytics, rules_compendium, soundscape, asset_forge, audience_studio (< 95 lines).
4. **Schema & File Invariants Suite (`tests/test_microfrontend_manifests/test_manifest_schema_invariants.py`)**:
   - Contract structure, component tags, and file length invariant verification (< 85 lines).
5. **Verification**:
   - Run `uv run pytest tests/test_microfrontend_manifests/` to confirm 100% pass rate.

## Definition of Done
- `tests/test_microfrontend_manifests.py` decomposed into `tests/test_microfrontend_manifests/` package.
- All extracted test modules strictly < 110 lines each per Hard Invariant 6.
- 100% test pass rate preserved across all microfrontend manifest checks.
