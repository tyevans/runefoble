---
id: '0679'
title: Spell Slot Restore Route on Character Sheet and Gateway Proxy
status: Complete
created: 2026-11-17
dependencies:
- TASK-0586
- TASK-0580
governing_adrs:
- ADR-0001
- ADR-0007
- ADR-0014
governing_prds:
- PRD-0016
- PRD-0006
governing_stories:
- US-0051
target_release: 0.9.0
---

# TASK-0679: Spell Slot Restore Route on Character Sheet and Gateway Proxy

## Status
Complete

## Summary
Characters can prepare and cast spells. No route restores spent spell slots. The App Shell cannot restore them, and no gateway route exists. This task adds the owner route in `character_sheet` and a gateway proxy.

## Problem Statement
- `services/character_sheet/src/character_sheet/router.py` exposes `POST .../spells/prepare` (line 49) and `POST .../spells/cast` (line 64). No restore route exists.
- The gateway has no spell route (TASK-0586 covers subresources that exist on the owner).
- The App Shell audit (work/0640) found no restore call.

## Documentation & Architecture Review
- ADR-0007: `character_sheet` owns spell slot state. The gateway proxies it.
- ADR-0001: the gateway checks the `edit` permission on the character before proxying.
- `docs/reference/ports-and-endpoints.md`: add both routes.

## Product & User Story References
- US-0051 (spellbook and slot tracking) and PRD-0016 (spell VFX and spell use) and PRD-0006 (character sheet).

## Detailed Specification & Implementation Plan
1. `character_sheet` aggregate: add `restore_spell_slots(level: int | None)`. Without a level, restore every level to its maximum. Emit a registered domain event (`@register_event`, inherits `BaseRunefobleEvent`).
2. Router: `POST /api/v1/characters/{character_id}/spells/restore` with an optional body `{ "slot_level": int }`. Return `CharacterState`.
3. Gateway: add the proxy route through the typed client (TASK-0580). Check `edit` on `character:{id}` through SpiceDB.
4. Update the event catalogue (`docs/reference/events-schema.md`).

## Frontdoor Blackbox Test Plan
- Create a character through the public API. Prepare and cast a level 1 spell twice. `GET` shows slots spent.
- `POST .../spells/restore` through the gateway. `GET` shows slots at maximum.
- A user without `edit` gets 403 from the gateway. The owner service is not called (double counts zero calls).

## Definition of Done
- Tests above pass. The event is registered and listed in `docs/reference/events-schema.md`.
- OpenAPI for `character_sheet` and the gateway lists the route.
- Changed files under 500 lines. `uv run pytest` and `make lint` pass.

## Audit Provenance

- Severity: medium
- Source audits: `work/0640.md`
