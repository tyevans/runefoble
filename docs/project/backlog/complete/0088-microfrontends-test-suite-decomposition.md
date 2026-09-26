---
id: 0088
title: Microfrontends Blackbox Test Suite Modular Decomposition
status: Complete
created: 2026-09-26
dependencies:
- TASK-0024
- TASK-0025
- TASK-0026
- TASK-0027
- TASK-0029
governing_adrs:
- ADR-0004
- ADR-0009
- ADR-0013
target_release: 0.2.0
pr_url: https://github.com/tyevans/runefoble/pull/75
governing_prds:
- PRD-0013
governing_stories:
- US-0004
---
# TASK-0088: Microfrontends Blackbox Test Suite Modular Decomposition

## Status
Refined

## Summary
Decompose `tests/test_microfrontends.py` (454 lines, 90.8% of limit) into two specialized blackbox test suites (`tests/test_microfrontend_manifests.py` and `tests/test_microfrontend_app_shell.py`) to prevent breaching Hard Invariant 6 (File length limit < 500 lines) as new service microfrontends are integrated.

## Problem Statement
`tests/test_microfrontends.py` currently stands at 454 lines. It tests two separate architectural layers:
1. Microfrontend manifest endpoints (`GET /ui/manifest`) and component metadata across all bounded context services (`board_state`, `character_sheet`, `game_session`, `the_watcher`, `voice_agent`, `asset_forge`).
2. App shell integration, Storybook configuration, package dependency cross-referencing, and Custom Element tag registration validation.

As new microfrontends are onboarded in Milestone 3 (such as `soundscape` and `campaign_lore`), this file will breach the 500-line hard invariant unless decomposed into focused, single-responsibility suites.

## Governing Architecture & ADRs
- **ADR-0004**: Lit Web Components & Storybook UI (microfrontend verification and isolation).
- **ADR-0009**: Continuous Backlog Refinement and Technical Debt Management.
- **ADR-0013**: Microfrontend Architecture and Service Component Vendoring (`/ui/manifest` contracts).

## Proposed Decomposition
1. **Service Manifests & Component Contracts Suite (`tests/test_microfrontend_manifests.py`)**:
   - `test_board_state_ui_manifest_frontdoor`, `test_character_sheet_ui_manifest_frontdoor`.
   - `test_game_session_ui_manifest_frontdoor`, `test_the_watcher_ui_manifest_frontdoor`, `test_voice_agent_ui_manifest_frontdoor`.
   - Component tags and package naming convention assertions.
   - Target length: < 220 lines.
2. **App Shell Orchestration & Storybook Aggregation Suite (`tests/test_microfrontend_app_shell.py`)**:
   - App shell Lit composition, Storybook stories indexing, and import graph verification.
   - Target length: < 220 lines.
3. **Original Monolith Deletion**:
   - Remove `tests/test_microfrontends.py`.

## INVEST Criteria Evaluation
- **Independent (I)**: Decomposes test file layout without altering runtime microfrontend manifests or App Shell code.
- **Negotiable (N)**: Test fixture factoring and test file division can be adjusted.
- **Valuable (V)**: Protects against Hard Invariant 6 violations (< 500 lines) and allows isolated manifest testing.
- **Estimable (E)**: Pure pytest suite decomposition.
- **Small (S)**: Scope strictly isolated to `tests/test_microfrontends.py`; all resulting files < 250 lines.
- **Testable (T)**: `uv run pytest tests/test_microfrontend_manifests.py tests/test_microfrontend_app_shell.py` confirms 100% pass rate.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Modular Test Suite Partitioning**:
   - `tests/test_microfrontends.py` decomposed into `tests/test_microfrontend_manifests.py` and `tests/test_microfrontend_app_shell.py`.
2. **Strict File Length Compliance (Hard Invariant 6)**:
   - All resulting test files strictly under 250 lines each.
3. **Frontdoor Blackbox Verification**:
   - 100% test pass rate across all existing microfrontend assertions via `GET /ui/manifest` and Storybook manifests.
4. **Original Monolith Removal**:
   - `tests/test_microfrontends.py` deleted.
5. **Quality Gates**:
   - Passes `uv run ruff check` and `uv run ruff format --check`.
