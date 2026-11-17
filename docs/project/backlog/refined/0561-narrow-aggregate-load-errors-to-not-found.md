---
id: '0561'
title: Narrow Aggregate Load Errors to Not-Found Across Services
status: Refined
created: 2026-11-17
dependencies:
- TASK-0560
governing_adrs:
- ADR-0007
- ADR-0011
governing_prds:
- PRD-0010
governing_stories:
- US-0010
target_release: 0.9.0
severity: high
source_audits:
- w2-soundscape.md
- w2-voice-agent.md
- w2-asset-forge.md
- w2-rules-compendium.md
- w2-campaign-lore.md
- w1-game-session.md
---

# TASK-0561: Narrow Aggregate Load Errors to Not-Found Across Services

## Status
Refined

## Summary
Several routers wrap `repo.load(...)` in `except Exception:` and replace the failure with an empty aggregate. A storage outage therefore creates a new empty stream with the same aggregate id. The next `save` then writes conflicting events. This task adds one shared `load_or_create` helper in `runefoble_platform` that catches only the "aggregate not found" case. Every other error reaches the caller as HTTP 503.

## Problem Statement
Evidence of the broad catch:
- `services/soundscape/src/soundscape/routers/cue.py:69`, `routers/tension.py:34` and `:88`, `routers/stems.py:123` and `:177`, `routers/leitmotif.py:118` and `:217`, `event_handlers.py:51`. A failed load returns `SoundscapeAggregate(agg_id)` (w2-soundscape F9). `GET /tension` then returns a canned tension of 10.
- `services/voice_agent/src/voice_agent/coordinator.py:61-63` replaces any load failure with an empty `VoiceRoomAggregate` (w2-voice-agent F6).
- `services/asset_forge/src/asset_forge/routers/battlemap.py`, `token.py`, and `print_forge.py` (`_record_aggregate`) do the same (w2-asset-forge F11).
- `services/rules_compendium/src/rules_compendium/routers/homebrew.py` (w2-rules-compendium F13).
- `services/campaign_lore/src/campaign_lore/` atlas read returns an empty atlas on any load error (w2-campaign-lore F20). Only the read path is changed here. Codex and retrieval state are in TASK-0572.
- `services/game_session/src/game_session/routers/bounties.py:90-91` hides load errors with `contextlib.suppress(Exception)` (w1-game-session F3). The index part is in TASK-0567. Only the load behavior is changed here.

## Documentation & Architecture Review
- AGENTS.md Hard Invariant 2: state flows through `AggregateRepository`. A silent reset breaks event history.
- ADR-0011 (eventsource-py) provides the not-found exception that this task must use. Confirm the exact class name in the installed `eventsource` package before coding.
- `docs/how-to/define-event-sourced-aggregates.md` must document `load_or_create` and the rule that only not-found may create a new aggregate.

## Product & User Story References
- [`prd-0010-adaptive-soundscape-foley-and-tension-scoring.md`](../../product/accepted/prd-0010-adaptive-soundscape-foley-and-tension-scoring.md)
- [`us-0010-redis-streams-domain-event-subscription.md`](../../user_stories/accepted/us-0010-redis-streams-domain-event-subscription.md)

## Detailed Specification & Implementation Plan
1. Add `load_or_create(repo, aggregate_id, factory)` to `libs/runefoble_platform/src/runefoble_platform/event_sourcing.py` (or a sibling module under 200 lines). It returns the loaded aggregate, creates a new one only on the library's not-found exception, and re-raises everything else.
2. Replace each `try: ... load ... except Exception:` block listed above with `load_or_create`. Delete the old blocks. No compatibility wrapper.
3. Map storage errors to HTTP 503 in the FastAPI exception handler for each service, using the existing error hierarchy in `runefoble_platform` errors.
4. Remove the `except Exception` in the soundscape `event_handlers.py:51` path. A handler failure is logged with the aggregate id and re-raised to the consumer, which applies the policy in TASK-0578.

## Frontdoor Blackbox Test Plan
- **Fail before, pass after:** inject a store that raises a connection error on `load` (a store double at the public `get_event_store` seam, not a private attribute). Call `GET /api/v1/soundscape/tension?session_id=...`. Before: 200 with tension 10. After: 503.
- **Fail before, pass after:** same double, call `POST /api/v1/voice/rooms/{id}/...` on a room that exists in the store. Before: a new empty room is saved. After: 503 and no new events are saved.
- **Pass before and after:** an unknown aggregate id on a read route returns the documented not-found response (404 or empty list as documented).
- Assertions use HTTP status codes and the event stream only.

## Definition of Done
1. `load_or_create` exists and is the only way routers create aggregates on load.
2. No `except Exception` surrounds a `repo.load` call in the listed files (grep is clean).
3. Storage errors produce 503 through the public API. Blackbox tests above pass.
4. `uv run pytest` and `make health-check` pass. Each changed file is under 500 lines.
5. How-to updated. `CHANGELOG.md` `[Unreleased]` entry added.

## Orchestrator Addenda (2026-11-17)

Source: `.audit/synth/discovered-round1.md`.

- `services/campaign_lore/src/campaign_lore/routers/documents.py:146-149` (`get_document`): `except Exception` around `repo.load` returns 404 for every error. Narrow to `AggregateNotFoundError`.

## Orchestrator Addenda (2026-11-17, round 2)

Source: `.audit/synth/discovered-round2.md`.

- services/the_watcher/src/the_watcher/routers/factions.py:199 get_faction maps every exception to 404. Map only not-found to 404 and let load failures raise.
