---
id: '0838'
title: The Watcher Narrates an Approved Audience Modifier
status: Refined
created: 2026-11-18
dependencies:
- TASK-0843
- TASK-0854
governing_adrs:
- ADR-0015
- ADR-0006
- ADR-0007
- ADR-0011
governing_prds:
- PRD-0011
governing_stories:
- US-0031
target_release: 0.9.0
---

# TASK-0838: The Watcher Narrates an Approved Audience Modifier

## Status
Refined

Decision (user, 2026-11-18): the narration goes to the DM first, as a private whisper. The DM sends it to the table or drops it. When the AI is unavailable, the DM gets a short notice and nothing goes to the players.

## Summary
The Watcher consumes `AudienceModifierApproved` on `runefoble.events.audience`. For each approved modifier, it asks the inference worker for narration (`POST /inference/v1/dm-narration`, the existing contract in `docs/reference/inference-worker-response-contract.md`) and records the text as a DM whisper in the session's `WatcherWhispers` aggregate. The DM sends a whisper of this kind to the table through a new route; that publishes `WatcherNarrativeDispatched`, which the table and the overlay show.

## Documentation & Architecture Review
- `docs/how-to/manage-dm-copilot-whispers-and-veto-overrides.md` (whisper routes, `session.control`, `<runefoble-dm-whisper-bar>`).
- `docs/how-to/orchestrate-audience-chaos-polls.md` (consumer contract), `docs/how-to/run-supervised-redis-stream-consumers.md`.
- Shared helper `runefoble_platform.audience_modifiers` (TASK-0843). Consumers are idempotent (TASK-0854).
- `docs/explanation/the-watcher-autonomous-dm.md`: The Watcher proposes; the DM keeps veto authority.
- ADR-0006, ADR-0007, ADR-0011, ADR-0015 (no canned text, fail loud).

## Product & User Story References
- [`prd-0011-live-spectator-studio-and-audience-interactivity.md`](../../product/accepted/prd-0011-live-spectator-studio-and-audience-interactivity.md)
- [`prd-0001-the-watcher-ai-dm-and-board-animator.md`](../../product/accepted/prd-0001-the-watcher-ai-dm-and-board-animator.md)
- [`us-0031-live-stream-audience-chaos-polls-and-rumors.md`](../../user_stories/accepted/us-0031-live-stream-audience-chaos-polls-and-rumors.md)

## Detailed Specification & Implementation Plan
1. Add a supervised consumer on `runefoble.events.audience` in the_watcher lifespan. Use the shared helper for the approved check and the campaign match. It acts on every approved modifier type; it does not apply effects (the owners do).
2. Build one narration request: `campaign_id`, `session_id`, and `recent_events` with one line that describes the modifier (type and parameters). Call the inference worker through the existing Watcher worker client.
3. Success: record a whisper with `kind: "audience_narration"`, the narration text, the sensory details, and `source_proposal_id`. The whisper is pending until the DM acts.
4. Failure (worker unreachable, 5xx, or `degraded: true`): record a whisper with `kind: "narration_unavailable"` and a short reason. Do not record any narration text. Do not publish anything to the table. Do not use a canned or mock text.
5. Idempotency: a second delivery of the same `proposal_id` records nothing new (check the whispers of the session for that `source_proposal_id`).
6. New DM route `POST /api/v1/watcher/whispers/{whisper_id}/dispatch` (requires `session.control`): only for an `audience_narration` whisper. The DM may send edited text in the body. It marks the whisper dispatched and publishes `WatcherNarrativeDispatched` (`runefoble.events.watcher.narrative_dispatched`) with the session id, the text and the source proposal id. A second dispatch answers 409. Add the gateway proxy row for the route.
7. `<runefoble-dm-whisper-bar>` shows a Send action on `audience_narration` whispers and shows `narration_unavailable` as a notice. Add a Storybook story for both.
8. Regenerate the event catalogue and update the docs above.

## Frontdoor Test Plan
With the real the_watcher lifespan, the shared Redis double, and a live loopback inference worker double at the process boundary:
- An approved modifier records one `audience_narration` whisper with the worker text; the DM reads it through `GET /api/v1/watcher/whispers`.
- The DM dispatches it (with edited text): `WatcherNarrativeDispatched` carries the edited text; a second dispatch answers 409; a player gets 403.
- The worker is down: one `narration_unavailable` whisper; no narration text; no dispatched event.
- A vetoed modifier and a modifier of another campaign record nothing. A redelivered message records nothing new.
- Unit test and story for the whisper bar Send action and the notice.

## INVEST Criteria Evaluation
Medium: one consumer, one route, one event, one UI change. Testable through a published standard event, public routes and the emitted event.

## Definition of Done
1. The test plan passes. 2. The story renders with zero console errors. 3. Docs and catalogue are current. 4. `make health-check` passes.
