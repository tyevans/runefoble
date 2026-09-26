---
id: 0018
title: Character Level Progression, Spell Slots & Spellbook Preparation
status: Complete
created: 2026-09-25
completed: 2026-09-26
dependencies: [TASK-0009]
governing_adrs: [ADR-0007, ADR-0011]
target_release: 0.1.0
governing_prds:
- PRD-0006
governing_stories:
- US-0015
- US-0051
---

# TASK-0018 — Character Level Progression, Spell Slots & Spellbook Preparation

## Status
Complete

## Summary
Implement character level progression, class-based spell slot scaling, spell preparation, and casting tracking within the `character_sheet` aggregate (US-0015, PRD-0001). Governed by Hard Invariant 7 (Blackbox TDD with Frontdoor Setup), all tests must interact strictly through the public HTTP frontdoor API (`POST /api/v1/characters/...`) to create characters, advance levels, prepare spells, and cast them with spell slot exhaustion checks.

## Scope & Changes
1. **Domain Events (`libs/runefoble_events/events.py`)**:
   - `CharacterLeveledUp`: `session_id`, `character_id`, `new_level`, `max_hp_increase`, `spell_slots`. (@register_event("runefoble.events.character.leveled_up"))
   - `SpellPrepared`: `session_id`, `character_id`, `spell_name`, `spell_level`. (@register_event("runefoble.events.character.spell_prepared"))
   - `SpellSlotExpended`: `session_id`, `character_id`, `spell_name`, `slot_level_used`, `remaining_slots`. (@register_event("runefoble.events.character.spell_slot_expended"))
2. **Aggregate Extension (`services/character_sheet/src/character_sheet/aggregate.py`)**:
   - Add level, XP, class spellbook, and spell slots state to `CharacterAggregate`.
   - Implement `@handles` methods for level up, spell preparation, and slot expenditure.
3. **Public Frontdoor Endpoints (`services/character_sheet/src/character_sheet/main.py`)**:
   - `POST /api/v1/characters/{id}/level-up`
   - `POST /api/v1/characters/{id}/spells/prepare`
   - `POST /api/v1/characters/{id}/spells/cast`
4. **Blackbox TDD Suite (`tests/test_blackbox_character_progression.py`)**:
   - Author blackbox test first using `TestClient(app)`.
   - Setup strictly via frontdoor `POST /api/v1/characters`.
   - Exercise level up, preparation, casting, and error responses (`INSUFFICIENT_SPELL_SLOTS`).
