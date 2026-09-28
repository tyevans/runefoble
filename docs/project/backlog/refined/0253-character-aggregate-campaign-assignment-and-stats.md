---
id: '0253'
title: Character Aggregate Campaign Assignment and Core Attributes Extension
status: Refined
created: 2026-09-27
dependencies:
- TASK-0009
- TASK-0077
governing_adrs:
- ADR-0002
- ADR-0007
governing_prds:
- PRD-0006
governing_stories:
- US-0015
- US-0064
- US-0069
target_release: 0.8.0
---
# TASK-0253: Character Aggregate Campaign Assignment and Core Attributes Extension

## Status
Refined

## Summary
Extend `CharacterState` and `CharacterAggregate` in `services/character_sheet/src/character_sheet/` to include core 5e character attributes (`subclass: str | None`, `armor_class: int`, `speed_ft: int`, `ability_scores: dict[str, int]`) and campaign assignment (`campaign_id: str | None`). Add the domain event `CharacterAssignedToCampaign` to `libs/runefoble_events/src/runefoble_events/events.py` and register it with `@register_event`.

## Problem Statement
The event-sourced `CharacterAggregate` and `CharacterState` currently track inventory, equipment, spell slots, and conditions, but lack fields for `campaign_id`, `subclass`, `armor_class`, `speed_ft`, and `ability_scores`. Furthermore, when a player assigns a character to a campaign from the roster, there is no domain event to capture this lifecycle state transition in the event stream, preventing downstream services (like `board_state` or `the_watcher`) from reacting to party roster changes.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/how-to/define-event-sourced-aggregates.md`: Creating declarative aggregates and handling events with `eventsource-py`.
  - `docs/reference/events-schema.md`: CloudEvents domain event schemas and conventions.
  - `docs/how-to/interact-with-character-sheet-and-inventory.md`: Character attributes and equipment slots.
- **Governing Architecture & ADRs**:
  - **ADR-0002: Domain Events via eventsource-py**: All state transitions flow through `@handles` methods on aggregates.
  - **ADR-0007: Domain-Driven Design Architecture**: Aggregate boundary integrity.

## Product & User Story References
- **Product Requirement**: [`prd-0006-digital-character-sheet-inventory-and-conditions.md`](../../product/accepted/prd-0006-digital-character-sheet-inventory-and-conditions.md)
- **User Stories**:
  - [`us-0015-character-inventory-equipment-tracking.md`](../../user_stories/accepted/us-0015-character-inventory-equipment-tracking.md)
  - [`us-0064-character-roster-management-and-party-assignment.md`](../../user_stories/accepted/us-0064-character-roster-management-and-party-assignment.md)
  - [`us-0069-character-sheet-inspector-and-active-session-binding.md`](../../user_stories/accepted/us-0069-character-sheet-inspector-and-active-session-binding.md)

## Detailed Specification & Implementation Plan
1. **Domain Event (`libs/runefoble_events/src/runefoble_events/events.py`)**:
   - Define `CharacterAssignedToCampaign(BaseRunefobleEvent)`:
     - `campaign_id: str | None`
     - `assigned_by: str`
   - Register event with `@register_event("character.assigned_to_campaign", schema_version=1)`.
2. **State Extension (`services/character_sheet/src/character_sheet/models.py`)**:
   - Add fields to `CharacterState`:
     - `campaign_id: str | None = None`
     - `subclass: str | None = None`
     - `armor_class: int = 10`
     - `speed_ft: int = 30`
     - `ability_scores: dict[str, int] = Field(default_factory=lambda: {"str": 10, "dex": 10, "con": 10, "int": 10, "wis": 10, "cha": 10})`
   - Update `CharacterState.initial()` factory method.
3. **Aggregate Mutation Handler (`services/character_sheet/src/character_sheet/aggregate.py`)**:
   - Add method `assign_campaign(campaign_id: str | None, assigned_by: str) -> None`.
   - Add `@handles(CharacterAssignedToCampaign)` to update `self._state.campaign_id`.
4. **Service Router & Schemas (`services/character_sheet/src/character_sheet/router.py`)**:
   - Add endpoint `PATCH /api/v1/characters/{character_id}/campaign` accepting `campaign_id: str | None`.
5. **Unit Tests**:
   - Test event serialization, replay, and aggregate state reconstitution.

## Definition of Done
- [ ] `CharacterAssignedToCampaign` event registered and serializable.
- [ ] `CharacterAggregate` handles assignment and updates `campaign_id`.
- [ ] `CharacterState` holds subclass, AC, speed, and ability scores.
- [ ] Unit tests pass and all files remain <500 lines.
