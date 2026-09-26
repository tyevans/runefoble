---
id: 0051
title: Character Level Progression, Spellbook Preparation & Spell Slot Scaling
persona: Marcus (Adventurer)
status: Accepted
created: 2026-09-26
governing_prd: PRD-0006
---

# US-0051 — Character Level Progression, Spellbook Preparation & Spell Slot Scaling

## Governing PRD
- [`PRD-0006: Character Sheet Inventory, Equipment & Condition Aggregation`](../../product/accepted/prd-0006-digital-character-sheet-inventory-and-conditions.md)

## Persona
Marcus (Adventurer) / Sarah (Absent Player)

## User Story

**As a** tabletop player advancing my spellcaster or martial hero,  
**I want to** level up my character, manage my spellbook, prepare daily spells, and scale spell slots through `CharacterAggregate`,  
**So that** my character sheet mathematically enforces slot expenditure and progression rules without manual arithmetic.

## Acceptance Criteria

1. **Class-Based Slot Progression**: Leveling up recalculates spell slots across spell tiers 1–9 according to class progression tables.
2. **Daily Spell Preparation**: Players can prepare a subset of known spells from their spellbook up to their daily preparation limit.
3. **Slot Exhaustion Checks**: Casting spells verifies available slots and decrements the corresponding spell tier, emitting `SpellSlotExpended`.
4. **Aggregate Auditability**: All level changes, preparations, and spell expenditures flow through `eventsource-py` events with verified replay.
