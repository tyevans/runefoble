---
id: '0009'
title: Character Sheet Equipment, Inventory & Conditions Aggregate
status: Complete
created: 2026-09-25
governing_prds:
- PRD-0006
governing_stories:
- US-0015
- US-0024
---

# TASK-0009: Character Sheet Equipment, Inventory & Conditions Aggregate

## Status
Complete

## Summary
Extended `CharacterAggregate` in `services/character_sheet/src/character_sheet/aggregate.py` with full event-sourced tracking for inventory items, equipment slots (`main_hand`, `off_hand`, `armor`), and gameplay status conditions. Added REST endpoints in `services/character_sheet/src/character_sheet/main.py` and unit tests in `tests/test_character_aggregate.py`.

## Key Changes
- `libs/runefoble_events/src/runefoble_events/events.py`:
  - Added `ItemAddedToInventory`, `ItemRemovedFromInventory`, `EquipmentSlotUpdated`, `ConditionApplied`, and `ConditionRemoved` events.
- `services/character_sheet/src/character_sheet/aggregate.py`:
  - Added `InventoryItem` and `ConditionState` models.
  - Added `inventory`, `equipment`, and `conditions` to `CharacterState`.
  - Implemented `add_inventory_item`, `remove_inventory_item`, `equip_item`, `apply_condition`, and `remove_condition`.
  - Added `@handles` event handlers for all new domain events.
- `services/character_sheet/src/character_sheet/main.py`:
  - Added endpoints `/api/v1/characters/{id}/inventory/add`, `/inventory/{item_id}/remove`, `/equipment`, `/conditions`.
- `tests/test_character_aggregate.py`:
  - Tested inventory mutations, equipment slot changes, condition management, event replay, and REST endpoints.

## Verification
- `uv run pytest`: 81/81 tests passed.
- `uv run ruff check .` & `uv run ruff format .`: Clean.
