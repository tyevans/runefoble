---
id: '0843'
title: One Helper for Approved Audience Modifier Consumers
status: Complete
created: 2026-11-18
dependencies: []
governing_adrs:
- ADR-0006
- ADR-0007
- ADR-0015
governing_prds:
- PRD-0011
governing_stories:
- US-0031
target_release: 0.9.0
---

# TASK-0843: One Helper for Approved Audience Modifier Consumers

## Status
Complete

Source: refactor round 2026-11-18 (user approved).

## Summary
Three consumers apply approved audience modifiers: `services/game_session/src/game_session/audience_weather.py`, `services/board_state/src/board_state/audience_hazard.py` and `services/character_sheet/src/character_sheet/audience_status.py`. Each one repeats the same steps: check the event type, check `approved is True`, filter by `modifier_type`, read and check parameters, and refuse a modifier of another campaign. Move the shared steps into one helper in `libs/runefoble_platform`. Each service keeps only its own effect.

## Documentation & Architecture Review
- `docs/how-to/run-supervised-redis-stream-consumers.md`, `docs/how-to/orchestrate-audience-chaos-polls.md`.
- ADR-0006, ADR-0007 (each owner applies its own effect), ADR-0015 (fail loud).

## Product & User Story References
- [`prd-0011-live-spectator-studio-and-audience-interactivity.md`](../../product/accepted/prd-0011-live-spectator-studio-and-audience-interactivity.md)
- [`us-0031-live-stream-audience-chaos-polls-and-rumors.md`](../../user_stories/accepted/us-0031-live-stream-audience-chaos-polls-and-rumors.md)

## Detailed Specification & Implementation Plan
1. Add a small helper (for example `runefoble_platform.audience_modifiers`) that takes the modifier type and returns the approved `AudienceModifierApproved` event or `None`, and a helper that raises one shared error type for a missing or bad parameter and for a campaign mismatch.
2. Rewrite the three consumers to use it. Each keeps its own effect code and its own owner check (which aggregate owns the campaign).
3. Keep the behaviour the same: the existing frontdoor tests for the three consumers must pass without change.
4. Document the helper in `docs/how-to/orchestrate-audience-chaos-polls.md` (consumer section).

## Frontdoor Test Plan
The existing modules `tests/test_blackbox_audience_weather_modifier.py`, `tests/test_blackbox_audience_hazard_modifier.py` and the character_sheet status modifier test pass unchanged.

## INVEST Criteria Evaluation
Small (S). Behaviour stays the same. Testable through the existing frontdoor tests.

## Definition of Done
1. One helper, three consumers use it. 2. Existing tests pass unchanged. 3. `make health-check` passes.
