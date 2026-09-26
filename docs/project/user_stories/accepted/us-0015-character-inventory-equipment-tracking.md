---
id: 0015
title: Event-Sourced Character Inventory, Equipment & Condition Tracking
status: Accepted
created: 2026-09-25
governing_prd: PRD-0006
---

# US-0015: Event-Sourced Character Inventory, Equipment & Condition Tracking

## Governing PRD
- [`PRD-0006: Character Sheet Inventory, Equipment & Condition Aggregation`](../../product/accepted/prd-0006-digital-character-sheet-inventory-and-conditions.md)

## Persona
Sarah (Absent Player) / Marcus (Adventurer)

## User Story
As a tabletop player managing my hero,
I want my inventory, equipped weapons/armor, carried gold, and status conditions to be tracked through the `CharacterAggregate` via eventsource-py,
So that my character sheet is always in a verified state and every item pickup, equip, and condition infliction is replayable from domain events.

## Acceptance Criteria
1. `CharacterAggregate` models inventory items, equipment slots (`main_hand`, `off_hand`, `armor`), and active status conditions.
2. Domain events `ItemAddedToInventory`, `ItemRemovedFromInventory`, `EquipmentSlotUpdated`, and `ConditionApplied` are emitted and persisted.
3. REST endpoints in `character_sheet` support adding items, equipping gear, and applying conditions.
4. Full aggregate state is reconstitution-verified across unit tests.
