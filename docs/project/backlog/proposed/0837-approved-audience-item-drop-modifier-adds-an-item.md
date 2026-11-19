---
id: '0837'
title: Approved Audience Item Drop Modifier Adds an Item to the Party
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

# TASK-0837: Approved Audience Item Drop Modifier Adds an Item to the Party

## Status
Proposed

## Summary
Apply an approved `item_drop` modifier. No party stash or ground loot model exists, so a product decision is needed first: does the item go to a character inventory, to a new party stash, or to a board loot token?

## Product & User Story References
- [`prd-0011-live-spectator-studio-and-audience-interactivity.md`](../../product/accepted/prd-0011-live-spectator-studio-and-audience-interactivity.md)
- [`us-0031-live-stream-audience-chaos-polls-and-rumors.md`](../../user_stories/accepted/us-0031-live-stream-audience-chaos-polls-and-rumors.md)

## Documentation & Architecture Review
- `docs/how-to/run-supervised-redis-stream-consumers.md` and the model consumer `services/board_state/src/board_state/forged_battlemap.py`.
- `docs/how-to/orchestrate-audience-chaos-polls.md`.
- ADR-0006, ADR-0007 (each owner applies its own effect), ADR-0011, ADR-0015 (fail loud).

## Open Questions
1. Which owner holds the dropped item?
2. If a party stash is needed, which bounded context owns it?
