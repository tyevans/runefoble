---
id: '0458'
title: Automated Player Achievement Engine and Milestone Badges Projection
status: Proposed
created: 2026-09-29
dependencies:
- TASK-0052
- TASK-0110
governing_adrs:
- ADR-0005
- ADR-0006
- ADR-0011
governing_prds:
- PRD-0012
governing_stories:
- US-0040
- US-0054
target_release: 0.9.0
---

# TASK-0458: Automated Player Achievement Engine and Milestone Badges Projection

## Status
Proposed

## Summary
Implement an automated player achievement evaluation engine and milestone badge projection pipeline in `services/campaign_analytics`. Ingest domain events (critical rolls, combat knockouts, monster defeats, flawless attendance streaks) over Redis Streams, evaluate rule-based criteria, persist unlocked achievement records in PostgreSQL and in-memory read models, and expose REST endpoints for querying campaign and character achievement badges.

## Problem Statement
PRD-0012 explicitly mandates "Player Achievement & Milestone Badges: Automatically derived milestones (e.g. 'Survived 100 Goblins', 'Most Critical Fumbles', 'Unbroken Attendance')". Currently, `services/campaign_analytics` only derives combatant damage, healing, and turn counts for MVP awards and logs generic milestones. There is no automated rules engine to derive player milestone badges from domain events, no schema or persistent table for tracking character achievements, and no API endpoints for the client or spectator overlay to query unlocked achievement badges.

## Governing Architecture & ADRs
- **ADR-0005: Platform Identity & PostgreSQL Persistence**: Persistent relational tables for analytical projections and achievement records.
- **ADR-0006: Redis Streams Distributed Domain Event Streaming**: Event-driven projection worker evaluating achievement conditions asynchronously.
- **ADR-0011: eventsource-py Core Event Sourcing**: Projections derived deterministically from standard domain events.

## Product & User Story References
- [`prd-0012-campaign-telemetry-and-living-chronicle-timeline.md`](../../product/accepted/prd-0012-campaign-telemetry-and-living-chronicle-timeline.md)
- [`us-0040-campaign-combat-telemetry-and-living-timeline.md`](../../user_stories/accepted/us-0040-campaign-combat-telemetry-and-living-timeline.md)
- [`us-0054-combat-spatial-heatmaps-and-party-damage-analytics.md`](../../user_stories/accepted/us-0054-combat-spatial-heatmaps-and-party-damage-analytics.md)

## Scope of Work
1. **Achievement Definitions and Evaluation Rules (`services/campaign_analytics/src/campaign_analytics/achievements/engine.py`)**:
   - Define canonical milestone achievements: "Survived 100 Goblins" (monster slayers), "Critical Fumble Master" (5 natural 1s in a session), "Deadeye Sniper" (3 natural 20s), "Clutch Lifesaver" (stabilizing an ally at 0 HP), "Unbroken Attendance" (5 consecutive sessions attended without stand-in).
   - Implement event-driven rules evaluator processing dice rolls, combat damage/knockouts, and session lifecycle events.
2. **Schema and Read-Model Storage (`services/campaign_analytics/src/campaign_analytics/achievements/storage.py`)**:
   - Create `achievements_table` in SQLAlchemy metadata with columns `(id, campaign_id, session_id, character_id, character_name, achievement_id, title, description, badge_icon, rarity, unlocked_at, progress_current, progress_target)`.
   - Update `CampaignAnalyticsStorage` to record unlocked achievements and query campaign/character achievements with in-memory fallback.
3. **REST Router Endpoints (`services/campaign_analytics/src/campaign_analytics/routers/achievements.py`)**:
   - `GET /api/v1/analytics/campaigns/{campaign_id}/achievements` returning unlocked campaign badges and progress stats.
   - `GET /api/v1/analytics/characters/{character_id}/achievements` returning individual character badges and trophy history.
4. **Frontdoor Blackbox Verification (`tests/test_blackbox_campaign_achievements.py`)**:
   - Test event ingestion driving achievement unlock progression, database persistence, and REST endpoint queries.

## Definition of Done
1. `engine.py`, `storage.py`, and `routers/achievements.py` implemented strictly < 200 lines each per Hard Invariant 6.
2. Canonical achievements evaluated correctly against domain event sequences.
3. REST endpoints exposed and registered in FastAPI application.
4. Blackbox test suite passes with 100% assertions via `uv run pytest tests/test_blackbox_campaign_achievements.py`.
