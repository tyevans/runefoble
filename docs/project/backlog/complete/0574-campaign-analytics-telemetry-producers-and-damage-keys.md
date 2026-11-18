---
id: '0574'
title: Campaign Analytics Combat Telemetry Producers and Character Damage Session Keys
status: Complete
created: 2026-11-17
dependencies:
- TASK-0578
governing_adrs:
- ADR-0006
- ADR-0002
governing_prds:
- PRD-0012
governing_stories:
- US-0040
- US-0054
target_release: 0.9.0
---

# TASK-0574: Campaign Analytics Combat Telemetry Producers and Character Damage Session Keys

## Status
Complete

## Summary
Combat turns and character damage never reach campaign analytics in production. Analytics handles `CombatRoundAdvanced`, but game session emits `InitiativeTurnAdvanced`, and nothing emits `CombatRoundAdvanced`. Damage events carry no session or campaign id, so their stats are keyed to the character id. This task makes analytics consume the events game session really emits, adds the owning session and campaign to health events, and replaces the synthetic test event with the real one.

## Problem Statement
- `CombatRoundAdvanced` is constructed nowhere in `services/` or `gateway/`. Game session publishes `InitiativeTurnAdvanced` at `services/game_session/src/game_session/routers/combat.py:150-152`. `services/campaign_analytics/src/campaign_analytics/event_handlers.py:155` handles only `CombatRoundAdvanced` (w2-campaign-analytics F3).
- `libs/runefoble_events/src/runefoble_events/character.py:36-42` `CharacterHealthChanged` has no `session_id` or `campaign_id`. `services/character_sheet/src/character_sheet/handlers/vitals.py:15-26` sets neither. `event_handlers.py` `extract_context` falls back to `aggregate_id` (the character id), so `get_mvp(campaign_id=<real>)` returns zero (w2-campaign-analytics F2).
- `tests/test_blackbox_campaign_analytics_ui/test_analytics_dashboard_ui.py:105-115` publishes the synthetic `CombatRoundAdvanced`, which hides the gap (F3).
- Test-gap: all worker tests use `MockAsyncRedis` (w2-campaign-analytics F14).

## Documentation & Architecture Review
- `docs/how-to/project-campaign-analytics-and-chronicle-timeline.md:14` names `CombatRoundAdvanced` as the encounter input. Correct it to the event actually emitted, or to both if the round event is added by the producer (choose one).
- ADR-0002 requires watcher-driven orchestration to use real events. The round number comes from game session.

## Product & User Story References
- [`us-0054-combat-spatial-heatmaps-and-party-damage-analytics.md`](../../user_stories/accepted/us-0054-combat-spatial-heatmaps-and-party-damage-analytics.md)
- [`us-0040-campaign-combat-telemetry-and-living-timeline.md`](../../user_stories/accepted/us-0040-campaign-combat-telemetry-and-living-timeline.md)

## Detailed Specification & Implementation Plan
1. Handle `InitiativeTurnAdvanced` in the analytics dispatcher (round number and active combatant). Remove the dependency on the unemitted `CombatRoundAdvanced` or make game session emit it. Pick one.
2. Add `session_id` and `campaign_id` to `CharacterHealthChanged`. Character sheet fills them from the owning session context. If the character has no session, the event carries an explicit null and analytics skips it. Do not use the character id as a fallback.
3. Update the events-schema entry for `CharacterHealthChanged`.
4. Rewrite the UI test to publish events game session really emits, through the public route on game session.
5. Add one integration test that runs against a real Redis container in the Kind stack (not the mock).

## Frontdoor Blackbox Test Plan
- **Fail before, pass after:** start combat through the public game session route, advance the initiative through the public route, damage a character through the public route, then `GET` the MVP for the campaign. Before: zero combatants. After: the character is counted.
- **Fail before, pass after:** the combat heatmap route returns damage points for the real campaign.
- Public routes and the real Redis stream only.

## Definition of Done
1. Analytics counts turns and damage from events emitted in production. Grep shows no unemitted handled event.
2. `CharacterHealthChanged` carries session and campaign ids.
3. Two tests above pass. Real-Redis integration test passes in the Kind stack.
4. `uv run pytest` and `make health-check` pass. Files under 500 lines.
5. Docs and events-schema corrected. `CHANGELOG.md` entry.

## Audit Provenance

- Severity: high
- Source audits: `w2-campaign-analytics.md`
