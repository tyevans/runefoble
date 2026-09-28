---
id: '0245'
title: Campaign Lore Dependencies and Permissions Modular Decomposition
status: Refined
created: 2026-09-27
dependencies:
- TASK-0047
- TASK-0106
- TASK-0198
governing_adrs:
- ADR-0001
- ADR-0003
- ADR-0007
governing_prds:
- PRD-0007
- PRD-0015
- PRD-0018
governing_stories:
- US-0050
- US-0058
target_release: 0.8.0
---

# TASK-0245: Campaign Lore Dependencies and Permissions Modular Decomposition

## Status
Refined

## Summary
Decompose `services/campaign_lore/src/campaign_lore/dependencies.py` (474 lines, 94.8% of limit — approaching the 500-line invariant limit) into modular submodules under `services/campaign_lore/src/campaign_lore/` (`permissions.py`, `codex_deps.py`, and `dependencies.py`), keeping all dependency and permission modules strictly < 150 lines per Hard Invariant 6, ADR-0001, ADR-0003, and ADR-0007.

## Problem Statement
`services/campaign_lore/src/campaign_lore/dependencies.py` has grown to 474 lines and is the largest Python source file in the repository, dangerously close to the 500-line hard invariant limit in Rule 6. It currently combines aggregate repository initializations (`LoreDocument`, `DiegeticHandout`, `Relic`, `Atlas`, `Codex`, `WestMarchesAtlas`), singleton retrieval engine instances, SpiceDB Zanzibar authorization checks for lore secrets, handouts, and relics, as well as complex codex permission evaluation, persistence routines, and session dependency classes (`CodexSessionDeps`). Any further modifications or addition of new endpoints will violate Hard Invariant 6 unless decomposed.

## Governing Architecture & ADRs
- **ADR-0001: Google Zanzibar / SpiceDB Fine-Grained Authorization**: Isolation of Zanzibar relationship writes, permission evaluations, and authorization helpers.
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean module layout and separation of single-responsibility modules within `services/campaign_lore/`.
- **ADR-0007: Domain-Driven Design Architecture**: Segregating infrastructure repositories, security/permission evaluation, and domain session dependencies.

## Detailed Specification & Implementation Plan
1. **Zanzibar Permissions Submodule (`services/campaign_lore/src/campaign_lore/permissions.py`)**:
   - Extract permission checkers: `check_user_can_read_secrets`, `check_user_can_view_campaign`, `check_user_can_interact_handout`, `check_user_can_inspect_relic`, and `check_user_can_play_campaign` (< 120 lines).
2. **Codex Dependencies Submodule (`services/campaign_lore/src/campaign_lore/codex_deps.py`)**:
   - Extract codex-specific permission logic and lifecycle helpers: `check_user_can_view_codex_entry`, `check_user_can_edit_codex_entry`, `require_campaign_view`, `load_codex_entry`, `write_codex_permissions`, `update_codex_permissions`, and `CodexSessionDeps` (< 140 lines).
3. **Core Dependencies Refactoring (`services/campaign_lore/src/campaign_lore/dependencies.py`)**:
   - Retain aggregate repository singletons, retrieval engine setup, test overrides (`set_west_marches_repo`, `set_spicedb_client`), and re-export modular utilities for 100% backward compatibility (< 120 lines).
4. **Verification**:
   - Verify all campaign lore tests pass cleanly via `uv run pytest tests/test_blackbox_campaign_lore/` and blackbox test suites.

## INVEST Criteria Evaluation
- **Independent (I)**: Refactoring is strictly isolated to `services/campaign_lore/` internal dependencies.
- **Negotiable (N)**: Dependency injection function signatures and FastAPI dependencies remain unchanged.
- **Valuable (V)**: Prevents Hard Invariant 6 breach in the repo's largest source file (474 lines -> < 150 lines).
- **Estimable (E)**: Pure refactoring of existing, well-tested Python logic.
- **Small (S)**: Scope restricted to extracting permission checkers and codex helpers into 2 focused submodules (< 150 lines each).
- **Testable (T)**: Frontdoor verification via FastAPI test clients, SpiceDB Zanzibar mocks, and existing blackbox tests.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Module Architecture**:
   - `services/campaign_lore/src/campaign_lore/dependencies.py` reduced to strictly < 150 lines.
   - `services/campaign_lore/src/campaign_lore/permissions.py` created and strictly < 150 lines.
   - `services/campaign_lore/src/campaign_lore/codex_deps.py` created and strictly < 150 lines.
2. **Frontdoor Verification**:
   - All campaign lore endpoints and blackbox tests pass via `uv run pytest tests/test_blackbox_campaign_atlas_and_codex.py` and campaign lore test suites.
   - Zero health check warnings for `services/campaign_lore/src/campaign_lore/dependencies.py`.
3. **Quality Gates**:
   - Code formatted and linted cleanly via `uv run ruff check .` and `uv run ruff format --check .`.
