---
id: '0838'
title: The Watcher Narrates an Approved Audience Modifier
status: Proposed
created: 2026-11-18
dependencies:
- TASK-0441
governing_adrs:
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
Proposed

## Summary
The Watcher consumes `AudienceModifierApproved` and composes narrative text about the twist through the inference worker port. A new event (for example `WatcherNarrativeDispatched`) carries the text.

## Product & User Story References
- [`prd-0011-live-spectator-studio-and-audience-interactivity.md`](../../product/accepted/prd-0011-live-spectator-studio-and-audience-interactivity.md)
- [`us-0031-live-stream-audience-chaos-polls-and-rumors.md`](../../user_stories/accepted/us-0031-live-stream-audience-chaos-polls-and-rumors.md)

## Documentation & Architecture Review
- `docs/how-to/run-supervised-redis-stream-consumers.md` and the model consumer `services/board_state/src/board_state/forged_battlemap.py`.
- `docs/how-to/orchestrate-audience-chaos-polls.md`.
- ADR-0006, ADR-0007 (each owner applies its own effect), ADR-0011, ADR-0015 (fail loud).

## Open Questions
1. The inference worker contract for narration (`docs/reference/inference-worker-response-contract.md`) has no narration call yet. Define it first.
2. When the worker is unavailable, the narration fails loud (ADR-0015). Decide how the DM sees that failure.
