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
1. `CharacterAggregate` manages `inventory: list[InventoryItem]`, `equipment: dict[str, str]`, `currency: dict[str, int]`, `conditions: dict[str, ConditionState]`, `level: int`, `spellbook: list[str]`, `prepared_spells: list[str]`, and `spell_slots: dict[int, int]`.
2. Domain events `ItemAddedToInventory`, `ItemRemovedFromInventory`, `EquipmentSlotUpdated`, `ConditionApplied`, `ConditionRemoved`, `CharacterLeveledUp`, `SpellPrepared`, `SpellSlotExpended` inherit from `BaseRunefobleEvent` and are registered in `EventRegistry`.
3. REST endpoints in `character_sheet` support adding items, equipping weapons/armor, toggling conditions, advancing character level, preparing spells, and casting spells with slot exhaustion checks.
4. Python tests verify event replay, aggregate reconstitution, and frontdoor blackbox workflows.

## Linked User Stories
- [`US-0015: Event-Sourced Character Inventory, Equipment & Condition Tracking`](../../user_stories/accepted/us-0015-character-inventory-equipment-tracking.md)
- [`US-0024: Natural Speech Equipment Swapping and Hands-Free Wake-Word`](../../user_stories/accepted/us-0024-natural-speech-equipment-swapping-and-wake-word.md)
- [`US-0051: Character Level Progression, Spellbook Preparation & Spell Slot Scaling`](../../user_stories/accepted/us-0051-character-level-progression-and-spellbook.md)

## Implementing Backlog Tasks
- [`TASK-0009: Character Sheet Equipment, Inventory & Conditions Aggregate`](../../backlog/complete/0009-character-inventory-equipment-conditions.md)
- [`TASK-0018: Character Level Progression, Spell Slots & Spellbook Preparation`](../../backlog/complete/0018-character-level-progression-spellbook.md)
- [`TASK-0041: FastMCP Gateway Server Modular Decomposition`](../../backlog/complete/0041-fastmcp-gateway-server-modular-decomposition.md)
- [`TASK-0077: Character Sheet API Router and Schemas Modular Decomposition`](../../backlog/complete/0077-character-sheet-api-router-and-schemas-decomposition.md)
- [`TASK-0107: Character Sheet UI Inventory Grid and Condition Indicator Microfrontend`](../../backlog/refined/0107-character-sheet-ui-inventory-and-conditions-microfrontend.md)
