---
id: '0461'
title: Absentee Player Session Telemetry and Audio Recap Companion API
status: Proposed
created: 2026-09-29
dependencies:
- TASK-0011
- TASK-0052
- TASK-0246
governing_adrs:
- ADR-0002
- ADR-0005
- ADR-0007
governing_prds:
- PRD-0002
- PRD-0012
governing_stories:
- US-0004
- US-0040
- US-0054
target_release: 0.9.0
---

# TASK-0461: Absentee Player Session Telemetry and Audio Recap Companion API

## Status
Proposed

## Summary
Implement a unified Absentee Player Telemetry Companion API and Gateway proxy route linking absent player character telemetry (damage taken under stand-in AI, stand-in penalty occurrences, clutch survival moments, and chronicle highlights) directly alongside the narrative audio recap stream. Enable returning players (Sarah) to query session metrics in parallel with audio recap playback, satisfying PRD-0012 Checkable Outcome 3.

## Problem Statement
PRD-0012 Checkable Outcome 3 explicitly requires: "Absent players can query past session stats alongside their audio recap." Currently, absent player chronicle audio recaps (TASK-0011, TASK-0055) and combat telemetry (TASK-0052, TASK-0110) are decoupled across distinct services with no unified composite endpoint or Gateway proxy. An absent player catching up on a missed session must either listen to the audio recap without visual telemetry context or navigate separate dashboards without knowing how their character performed under stand-in control.

## Governing Architecture & ADRs
- **ADR-0002: Real-Time Audio Streaming and STT/TTS**: Synthesis and playback metadata for absentee audio recaps.
- **ADR-0005: Platform Identity & PostgreSQL Persistence**: SpiceDB Zanzibar campaign membership authorization checks.
- **ADR-0007: Domain-Driven Design Architecture**: Cross-service orchestration between `voice_agent`, `game_session`, and `campaign_analytics`.

## Product & User Story References
- [`prd-0002-missing-player-ai-stand-in-with-penalties.md`](../../product/accepted/prd-0002-missing-player-ai-stand-in-with-penalties.md)
- [`prd-0012-campaign-telemetry-and-living-chronicle-timeline.md`](../../product/accepted/prd-0012-campaign-telemetry-and-living-chronicle-timeline.md)
- [`us-0004-missing-player-ai-stand-in.md`](../../user_stories/accepted/us-0004-missing-player-ai-stand-in.md)
- [`us-0040-campaign-combat-telemetry-and-living-timeline.md`](../../user_stories/accepted/us-0040-campaign-combat-telemetry-and-living-timeline.md)

## Scope of Work
1. **Absentee Session Telemetry Aggregation (`services/campaign_analytics/src/campaign_analytics/routers/absentee.py`)**:
   - Implement `GET /api/v1/analytics/campaigns/{campaign_id}/sessions/{session_id}/absentee/{character_id}`.
   - Aggregate character damage taken, damage dealt, stand-in penalty events ("drunk", "foolishness"), zero-HP stabilization triggers, and narrative recap summary.
   - Attach audio recap stream URL (`/api/v1/voice/recap/{session_id}/{character_id}/audio.mp3`) and timestamp cues.
2. **Gateway Zanzibar Authorization Proxy (`gateway/api/src/gateway_api/routers/hub_views.py`)**:
   - Expose Gateway route `/api/v1/analytics/campaigns/{campaign_id}/sessions/{session_id}/absentee/{character_id}`.
   - Verify caller has Zanzibar permission `read` on `campaign:{campaign_id}`.
3. **Timeline Audio Scrubber Integration (`services/campaign_analytics/ui/src/runefoble-chronicle-timeline.ts`)**:
   - Connect `play-audio-recap` events to the absentee companion data, highlighting relevant combat rounds and spatial coordinates on the map while audio plays.
4. **Frontdoor Blackbox Verification (`tests/test_blackbox_absentee_telemetry_companion.py`)**:
   - Verify endpoint queries return consolidated telemetry and audio recap metadata with 200 OK.
   - Verify unauthorized callers receive 403 Forbidden via SpiceDB Zanzibar checks.

## Definition of Done
1. `routers/absentee.py` and modified `hub_views.py` remain strictly < 200 lines each.
2. Gateway endpoint enforces SpiceDB Zanzibar campaign membership.
3. Audio recap URL and character session telemetry returned in unified response payload.
4. Blackbox test suite passes with 100% assertions via `uv run pytest tests/test_blackbox_absentee_telemetry_companion.py`.
