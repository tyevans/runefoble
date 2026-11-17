---
id: '0570'
title: Character Sheet Unprepare Spell and Stand-In Activation as Persisted Events
status: Refined
created: 2026-11-17
dependencies:
- TASK-0560
governing_adrs:
- ADR-0011
- ADR-0007
governing_prds:
- PRD-0002
- PRD-0006
governing_stories:
- US-0025
- US-0026
- US-0051
target_release: 0.9.0
severity: high
source_audits:
- w1-character-sheet.md
---

# TASK-0570: Character Sheet Unprepare Spell and Stand-In Activation as Persisted Events

## Status
Refined

## Summary
Two character mutations change state without an event. `unprepare_spell` removes a prepared spell in memory only, so the spell returns after a reload. `set_stand_in_active` writes the stand-in flag directly, so no caller activates it and the guardrail and permadeath checks never see it. This task adds `SpellUnprepared`, `StandInActivated`, and `StandInReleased` events and removes the direct writes.

## Problem Statement
- `services/character_sheet/src/character_sheet/handlers/spells.py:60-63`: `unprepare_spell` sets `self._state` without `create_event`. A probe shows `[]` from the mutation and `['Shield']` on a fresh GET (w1-character-sheet F3).
- `services/character_sheet/src/character_sheet/handlers/vitals.py:65-66`: `set_stand_in_active` writes `_state` directly. No caller exists in `character_sheet` or `gateway/api`. The guardrail at `handlers/spells.py:76` and permadeath at `handlers/vitals.py:32` cannot see the flag (w1-character-sheet F4).
- The gateway keeps its own `is_stand_in_active` in `gateway_api/character_store_mutations.py:62`. The gateway store is outside this task (gateway theme). The character aggregate becomes the source of truth.
- `/healthz` and the BDD reload test verify only the in-memory store (w1-character-sheet F15). Restart coverage is added here.

## Documentation & Architecture Review
- AGENTS.md Hard Invariant 2.
- `docs/how-to/configure-stand-in-guardrails-and-hot-swap.md` describes activation. Verify it and correct it.
- `docs/reference/events-schema.md` needs the new event types.

## Product & User Story References
- [`us-0025-personalized-ai-stand-in-tactical-policies.md`](../../user_stories/accepted/us-0025-personalized-ai-stand-in-tactical-policies.md)
- [`us-0026-mid-session-hot-swap-takeover-and-permadeath-lock.md`](../../user_stories/accepted/us-0026-mid-session-hot-swap-takeover-and-permadeath-lock.md)
- [`prd-0002-missing-player-ai-stand-in-with-penalties.md`](../../product/accepted/prd-0002-missing-player-ai-stand-in-with-penalties.md)

## Detailed Specification & Implementation Plan
1. Add `SpellUnprepared` (`@register_event`) emitted by `unprepare_spell`, handled with `@handles`.
2. Add `StandInActivated` and `StandInReleased` events. `set_stand_in_active` becomes a command that emits one of them. Delete the direct `_state` write.
3. Expose the activation as a public route on the character service: `POST /api/v1/characters/{id}/stand-in`. The game session hot-swap path calls this route (through the public API), not a private method.
4. The aggregate reads `is_stand_in_active` from its own state for the guardrail and permadeath checks.

## Frontdoor Blackbox Test Plan
- **Fail before, pass after:** prepare then unprepare a spell through public routes, restart the app, GET the character. Before: the spell is back. After: the spell is absent.
- **Fail before, pass after:** activate stand-in through the new route, restart, then request a permadeath-relevant HP change. Before: permadeath lock not applied. After: the lock applies.
- Assertions use HTTP and the character event stream.

## Definition of Done
1. No direct `_state` assignment in `handlers/`. Grep clean.
2. Restart tests pass. New events registered and documented.
3. `uv run pytest` and `make health-check` pass. Files under 500 lines.
4. `CHANGELOG.md` entry.
