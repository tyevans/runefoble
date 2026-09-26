---
id: '0077'
title: Character Sheet API Router and Schemas Modular Decomposition
status: Proposed
created: 2026-09-26
dependencies: [TASK-0009, TASK-0018]
governing_adrs: [ADR-0003, ADR-0011]
target_release: 0.2.0
---

# TASK-0077: Character Sheet API Router and Schemas Modular Decomposition

## Status
Proposed

## Summary
Decompose `services/character_sheet/src/character_sheet/main.py` (302 lines, 60.4% of limit) into dedicated Pydantic request schema modules (`schemas.py`), endpoint routing controllers (`router.py`), and a lean application entrypoint (`main.py`) adhering to the modular pattern established in TASK-0040.

## Problem Statement
`services/character_sheet/src/character_sheet/main.py` currently embeds:
1. 8+ Pydantic request models (`CreateCharacterRequest`, `HealthChangeRequest`, `PenaltyRequest`, `AddInventoryItemRequest`, `RemoveInventoryItemRequest`, `EquipItemRequest`, `LevelUpRequest`, `PrepareSpellRequest`, `CastSpellRequest`).
2. 12+ HTTP endpoints handling character lifecycle, HP adjustments, inventory operations, and spellbook preparation.
3. FastAPI application creation, lifespan event bus initialization, and aggregate repository wiring.

As upcoming Milestone 3 features introduce TTRPG Rules Compendiums (TASK-0048) and Campaign Lore RAG (TASK-0047), character sheet endpoints will expand with feat selection, skill proficiencies, and multiclassing, quickly pushing `main.py` beyond the 500-line invariant.

## Proposed Decomposition
1. **Pydantic Schemas (`services/character_sheet/src/character_sheet/schemas.py`)**:
   - Extract all character creation, HP, penalty, inventory, and spellcasting request models (< 120 lines).
2. **APIRouter Endpoint Controller (`services/character_sheet/src/character_sheet/router.py`)**:
   - Extract HTTP endpoint handlers into a modular FastAPI `APIRouter` with dependency-injected aggregate repository (< 170 lines).
3. **Application Entrypoint (`services/character_sheet/src/character_sheet/main.py`)**:
   - Retain FastAPI instance, OpenAPI metadata, lifespan/event-store initialization, and router inclusion (`app.include_router(router)`) (< 70 lines).

## INVEST Criteria Evaluation
- **Independent (I)**: Refactors internal code organization without changing any external HTTP endpoints, request/response bodies, or aggregate logic.
- **Negotiable (N)**: Sub-router grouping (e.g. inventory vs spellcasting sub-routers) can be adjusted as features expand.
- **Valuable (V)**: Protects against Hard Invariant 6 violations (< 500 lines) and standardizes FastAPI architecture across bounded contexts.
- **Estimable (E)**: Follows the proven APIRouter extraction pattern applied in TASK-0040.
- **Small (S)**: Scope strictly isolated to `services/character_sheet/src/character_sheet/main.py`; all resulting files < 180 lines.
- **Testable (T)**: Verified with `uv run pytest tests/test_character_aggregate.py tests/test_blackbox_character_progression.py`.

## Acceptance Criteria
1. `services/character_sheet/src/character_sheet/main.py` decomposed into `schemas.py`, `router.py`, and a lean `main.py` strictly under 180 lines each.
2. 100% test pass rate across all character sheet unit and blackbox progression tests.
3. Conforms strictly to Hard Invariant 6 (< 500 lines per file).
4. Zero breaking changes to REST route signatures or OpenAPI schemas.
