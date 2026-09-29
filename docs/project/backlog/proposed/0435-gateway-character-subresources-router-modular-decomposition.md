---
id: '0435'
title: Gateway Character Subresources Router Modular Decomposition
status: Proposed
created: 2026-09-28
dependencies:
- TASK-0356
- TASK-0357
governing_adrs:
- ADR-0001
- ADR-0007
- ADR-0013
governing_prds:
- PRD-0006
- PRD-0023
governing_stories:
- US-0015
- US-0051
- US-0064
- US-0069
target_release: 0.9.0
---

# TASK-0435: Gateway Character Subresources Router Modular Decomposition

## Status
Proposed

## Summary
Decompose `gateway/api/src/gateway_api/routers/character_subresources.py` (357 lines, 71.4% of limit) into modular domain sub-routers under `gateway/api/src/gateway_api/routers/characters/` (`health.py`, `inventory.py`, `conditions.py`, `spells.py`, `guardrails.py`), ensuring all subresource router modules remain strictly < 120 lines per Hard Invariant 6.

## Problem Statement
`gateway/api/src/gateway_api/routers/character_subresources.py` bundles health point adjustments, equipment item slot assignments, inventory additions and removals, active condition applications/clearing, spell slot preparation and casting, and stand-in guardrails persistence proxies into a single monolithic 357-line router. As feats, proficiencies, resting mechanics, and spell level filtering are expanded, this file will rapidly approach the 500-line invariant limit unless modularized into focused, single-responsibility sub-routers.

## Governing Architecture & ADRs
- **ADR-0001: Google Zanzibar for Fine-Grained Authorization**: Preserves object-level permission dependencies on every subresource route (`edit` on `character:{character_id}`).
- **ADR-0007: Domain-Driven Design Architecture**: Clean domain segregation for character sub-domains (vitality, equipment, statuses, magic, autonomous directives).
- **ADR-0013: Modular Decomposition**: All source files kept strictly < 500 lines (sub-routers < 120 lines).

## Product & User Story References
- [`prd-0006-digital-character-sheet-inventory-and-conditions.md`](../../product/accepted/prd-0006-digital-character-sheet-inventory-and-conditions.md)
- [`prd-0023-unified-frontend-application-shell-and-campaign-hub.md`](../../product/accepted/prd-0023-unified-frontend-application-shell-and-campaign-hub.md)
- [`us-0015-dynamic-equipment-slots-and-encumbrance.md`](../../user_stories/accepted/us-0015-dynamic-equipment-slots-and-encumbrance.md)
- [`us-0051-character-sheet-inventory-equipment-and-conditions.md`](../../user_stories/accepted/us-0051-character-sheet-inventory-equipment-and-conditions.md)

## Scope of Work
1. **Health Sub-Router (`gateway/api/src/gateway_api/routers/characters/health.py`)**:
   - Extract `POST /api/v1/characters/{character_id}/health` (< 70 lines).
2. **Inventory & Equipment Sub-Router (`gateway/api/src/gateway_api/routers/characters/inventory.py`)**:
   - Extract `POST /api/v1/characters/{character_id}/equipment`, `POST /api/v1/characters/{character_id}/inventory`, `DELETE /api/v1/characters/{character_id}/inventory/{item_id}` (< 110 lines).
3. **Conditions Sub-Router (`gateway/api/src/gateway_api/routers/characters/conditions.py`)**:
   - Extract `POST /api/v1/characters/{character_id}/conditions` and `DELETE /api/v1/characters/{character_id}/conditions/{condition}` (< 80 lines).
4. **Spells Sub-Router (`gateway/api/src/gateway_api/routers/characters/spells.py`)**:
   - Extract `POST /api/v1/characters/{character_id}/spells/cast` and `POST /api/v1/characters/{character_id}/spells/prepare` (< 80 lines).
5. **Stand-In Guardrails Sub-Router (`gateway/api/src/gateway_api/routers/characters/guardrails.py`)**:
   - Extract `PUT /api/v1/characters/{character_id}/guardrails` (< 60 lines).
6. **Aggregator Router (`gateway/api/src/gateway_api/routers/character_subresources.py`)**:
   - Aggregate sub-routers into single parent router preserving complete route path backwards compatibility (< 40 lines).
7. **Verification**:
   - Verify blackbox character mutations test suite: `uv run pytest tests/test_blackbox_character_sheet_mutations.py tests/test_blackbox_character_management_and_vtt_sync.py`.

## Definition of Done
- `character_subresources.py` reduced to strictly < 50 lines.
- Extracted sub-routers under `routers/characters/` strictly < 120 lines each.
- All character sheet mutation tests pass with 100% assertions.
- Code passes `uv run ruff check .` and `uv run ruff format --check .`.
