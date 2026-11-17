---
id: '0564'
title: Stop Suppressing Domain Event Publish Failures and Fail DM Decisions Loudly
status: Refined
created: 2026-11-17
dependencies:
- TASK-0562
governing_adrs:
- ADR-0006
- ADR-0002
- ADR-0007
governing_prds:
- PRD-0001
governing_stories:
- US-0017
target_release: 0.9.0
severity: high
source_audits:
- w3-event-wiring.md
- w1-the-watcher.md
- w2-asset-forge.md
- w1-game-session.md
---

# TASK-0564: Stop Suppressing Domain Event Publish Failures and Fail DM Decisions Loudly

## Status
Refined

## Summary
Eighty publish call sites were found. Forty-six wrap the call in `contextlib.suppress(Exception)`. A DM veto, approval, or dice roll can change state while its audit event is lost, and the request still returns success. This task replaces suppression with a logged, counted failure. Decision routes that change state return 503 when the event cannot be published.

## Problem Statement
- `services/the_watcher/src/the_watcher/routers/copilot/actions.py:75-77` (WatcherActionProposed), `:110-112` (WatcherActionVetoed), `:150-152` (WatcherActionApproved), `:197-199` (WatcherActionModified). `routers/copilot/whispers.py:106-108`, `routers/autonomous_dm.py:39-42`, `:61-64`, `:83-86`, `routers/stand_in.py:99-102`, and `routers/intent/speech.py:96-100` follow the same pattern (w1-the-watcher F7).
- `services/game_session/src/game_session/routers/session.py:68`, `routers/tavern.py:123` (w3-event-wiring F9). The session route part is refactored in TASK-0565.
- `services/asset_forge/src/asset_forge/dependencies.py` `publish_forge_event` suppresses both the in-memory and Redis publish (w2-asset-forge F13).
- `services/soundscape/src/soundscape/dependencies.py` `publish_soundscape_event` suppresses every exception (w2-soundscape F9).
- `services/game_session/src/game_session/routers/session.py:205-207` suppresses the dice-roll publish (w1-game-session F6, handled in TASK-0565).

## Documentation & Architecture Review
- AGENTS.md Hard Invariant 2 and the Watcher principle ("assistant, never dictator") require that a human veto is recorded. An unrecorded veto is a defect.
- ADR-0006 expects publish failures to be visible. This task defines the policy: non-state routes log and count the failure. State-changing decision routes return 503.
- `docs/reference/events-schema.md` does not describe failure behavior. Add a short section in `docs/reference/redis-streams-event-bus.md`.

## Product & User Story References
- [`prd-0001-the-watcher-ai-dm-and-board-animator.md`](../../product/accepted/prd-0001-the-watcher-ai-dm-and-board-animator.md)
- [`us-0017-human-dm-veto-and-narrative-copilot-whispers.md`](../../user_stories/accepted/us-0017-human-dm-veto-and-narrative-copilot-whispers.md)

## Detailed Specification & Implementation Plan
1. Add `publish_or_fail(bus, stream, event)` to `runefoble_platform` (`redis_bus.py` neighbor module). It awaits `publish_event`, logs at error level with stream and event type, increments a counter, and re-raises a `DomainEventPublishError`.
2. Add `publish_best_effort(bus, stream, event)` for read-model side effects. It logs and counts, and does not raise.
3. Decision routes (veto, approve, modify, whisper, stand-in activation, DM mutation) use `publish_or_fail`. The FastAPI handler maps `DomainEventPublishError` to 503. The aggregate save happens before publish, so a 503 must be retried by the client. Document this.
4. All other call sites in the listed files use `publish_best_effort`. Remove every `contextlib.suppress(Exception)` around publish.
5. `/healthz` in each service reports `event_publish_failures` as a count.

## Frontdoor Blackbox Test Plan
- **Fail before, pass after:** a Redis-shaped double that raises on `publish_event`. Call the public veto route on a pending action. Before: 200 and the action is vetoed with no audit event. After: 503 and the action is still pending.
- **Fail before, pass after:** with the same double, call a non-decision route (for example a read-model update). Before: 200 with silent loss. After: 200 and `event_publish_failures` increments on `/healthz`.
- Assertions use HTTP status codes, `/healthz`, and the stream reader of the double.

## Definition of Done
1. No `contextlib.suppress(Exception)` wraps a publish call in `services/` or `gateway/` (grep clean).
2. Decision routes return 503 on publish failure. Blackbox tests above pass.
3. `uv run pytest` and `make health-check` pass. Changed files under 500 lines.
4. Reference doc describes the policy. `CHANGELOG.md` entry.
