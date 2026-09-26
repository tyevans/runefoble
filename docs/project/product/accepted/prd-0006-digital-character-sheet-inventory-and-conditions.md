# PRD-0006: Character Sheet Inventory, Equipment & Condition Aggregation

## Status
Accepted

## Purpose
Character sheets in Runefoble must track active equipment, inventory capacity, currency, and gameplay conditions (both 5e/d20 standard conditions like `blinded` or `prone`, and Runefoble absence penalties like `drunk` and `foolishness`). All mutations must flow strictly through `CharacterAggregate` backed by eventsource-py for full event replay and auditability.

## Personas & User Needs
- **Marcus (Adventurer)**: Equips magic items (e.g. `Longsword +1`, `Chain Mail`), updates encumbrance, and tracks carried potions.
- **Sarah (Absent Player)**: Returns to find clear record of gold spent, potions consumed, and conditions inflicted while her AI stand-in was active.
- **The Watcher (Autonomous DM)**: Queries inventory to confirm spell components and items before resolving actions.

## Checkable Outcomes
1. `CharacterAggregate` manages `inventory: list[InventoryItem]`, `equipment: dict[str, str]`, `currency: dict[str, int]`, and `conditions: dict[str, ConditionState]`.
2. Domain events `ItemAddedToInventory`, `ItemRemovedFromInventory`, `EquipmentSlotUpdated`, `ConditionApplied`, `ConditionRemoved` inherit from `BaseRunefobleEvent` and are registered in `EventRegistry`.
3. REST endpoints in `character_sheet` support adding items, equipping weapons/armor, and toggling conditions.
4. Python tests verify event replay and aggregate reconstitution.
