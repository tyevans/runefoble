---
id: '0088'
title: Microfrontends Blackbox Test Suite Modular Decomposition
status: Proposed
created: 2026-09-26
dependencies: [TASK-0024, TASK-0025, TASK-0026, TASK-0027, TASK-0029]
governing_adrs: [ADR-0004, ADR-0009, ADR-0013]
target_release: 0.2.0
---

# TASK-0088: Microfrontends Blackbox Test Suite Modular Decomposition

## Status
Proposed

## Summary
Decompose `tests/test_microfrontends.py` (386 lines, 77.2% of limit) into two specialized blackbox test suites (`tests/test_microfrontend_manifests.py` and `tests/test_microfrontend_app_shell.py`) to prevent breaching Hard Invariant 6 (File length limit < 500 lines) as new service microfrontends (e.g. campaign lore RAG, encounter builder) are onboarded.

## Problem Statement
`tests/test_microfrontends.py` currently stands at 386 lines. It tests two separate architectural layers:
1. Microfrontend manifest endpoints (`GET /ui/manifest`) and component metadata across all five bounded context services (`board_state`, `character_sheet`, `game_session`, `the_watcher`, `voice_agent`).
2. App shell integration, Storybook configuration, package dependency cross-referencing, and Custom Element tag registration validation.

As new microfrontends are integrated in Milestone 3 (such as `campaign_lore` and `rules_compendium`), this monolith will exceed 500 lines and violate Hard Invariant 6.

## Proposed Decomposition
1. **Service Manifests & Component Contracts Suite (`tests/test_microfrontend_manifests.py`)**:
   - `test_board_state_ui_manifest_frontdoor`, `test_character_sheet_ui_manifest_frontdoor`.
   - `test_game_session_ui_manifest_frontdoor`, `test_the_watcher_ui_manifest_frontdoor`, `test_voice_agent_ui_manifest_frontdoor`.
   - Component tags and package naming convention assertions.
   - Target length: < 180 lines.
2. **App Shell Orchestration & Storybook Aggregation Suite (`tests/test_microfrontend_app_shell.py`)**:
   - App shell Lit composition, Storybook stories indexing, and import graph verification.
   - Target length: < 160 lines.
3. **Original Monolith Deletion**:
   - Remove `tests/test_microfrontends.py`.

## INVEST Criteria Evaluation
- **Independent (I)**: Decomposes test file layout without altering runtime microfrontend manifests or App Shell code.
- **Negotiable (N)**: Test fixture factoring and test file division can be adjusted.
- **Valuable (V)**: Protects against Hard Invariant 6 violations (< 500 lines) and allows isolated manifest testing.
- **Estimable (E)**: Pure pytest suite decomposition.
- **Small (S)**: Scope strictly isolated to `tests/test_microfrontends.py`; all resulting files < 190 lines.
- **Testable (T)**: `uv run pytest tests/test_microfrontend_manifests.py tests/test_microfrontend_app_shell.py` confirms 100% pass rate.

## Acceptance Criteria
1. `tests/test_microfrontends.py` decomposed into modular test suites strictly under 200 lines each.
2. 100% test pass rate across all existing microfrontend assertions.
3. Conforms strictly to Hard Invariant 6 (< 500 lines per file).
4. Code quality verified with `uv run ruff check` and `uv run ruff format --check`.
