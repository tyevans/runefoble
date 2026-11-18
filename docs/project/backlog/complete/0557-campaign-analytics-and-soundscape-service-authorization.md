---
id: '0557'
title: Campaign Analytics and Soundscape Service Fail-Closed Authorization
status: Complete
created: 2026-11-17
dependencies:
- TASK-0520
- TASK-0541
- TASK-0542
- TASK-0540
- TASK-0527
- TASK-0528
- TASK-0536
governing_adrs:
- ADR-0001
- ADR-0007
- ADR-0014
governing_prds:
- PRD-0012
- PRD-0010
governing_stories:
- US-0040
- US-0054
- US-0039
- US-0053
target_release: 0.9.0
---

# TASK-0557: Campaign Analytics and Soundscape Service Fail-Closed Authorization

## Status
Complete

## Summary
The analytics service and the soundscape service each have a permission helper that returns success when no user header is present. The gateway proxies do not forward a subject, so every gateway call is allowed by the service. The soundscape service also has four mutating routes with no check at all, and its gateway routing (TASK-0436) misses two of them. This task makes both services require a verified subject from the gateway, and it binds each route to its schema permission.

## Problem Statement
- `services/campaign_analytics/src/campaign_analytics/dependencies.py:82` returns True ("Public viewing permitted when no user specified") when `X-User-ID` is absent. The gateway proxy (`gateway/api/src/gateway_api/routers/hub_views.py:16-24`) sends no user header, so every gateway call passes the service check (`w2-campaign-analytics.md` F7).
- `services/soundscape/src/soundscape/dependencies.py:121-122` (`check_user_can_control_soundscape`): `if not user_id: return True` (`w2-soundscape.md` F7).
- Soundscape routes with no check: `routers/stems.py:60` (`POST /api/v1/soundscape/stems/volume`), `routers/stems.py:166` (`POST /api/v1/soundscape/duck`), `routers/tension.py:69` (`POST /api/v1/soundscape/tension/calculate`), and `routers/stems.py:87` (override, which uses the fail-open helper). Route `POST /api/v1/soundscape/cue` (`routers/cue.py:32`) and `routers/leitmotif.py:89,182` use the fail-open helper (`w3-authz-coverage.md` rows 249-256).
- The soundscape service trusts an `x-user-id` header that the gateway does not set (`w2-soundscape.md` F7). Identity is the verified principal from TASK-0520.
- TASK-0436 (proposed or refined gateway proxy) covers `/cue`, `/tension/calculate`, `/stems/override`, and `/leitmotif`. It does not cover `/stems/volume` or `/duck`. See the index report for the correction.
- `services/soundscape/src/soundscape/dependencies.py:51` reads `spicedb_token` (`w3-ddd-architecture.md` F9). TASK-0625 fixes the setting. TASK-0541 replaces the factory.

## Documentation & Architecture Review
- ADR-0001: soundscape controls check `session.control` (DM and session controls). Player-visible reads check `session.observe`. Campaign-scoped actions check `campaign.run_session` or `campaign.manage`.
- ADR-0007: the analytics context owns telemetry projections. The soundscape context owns mixer state. Both read the campaign grant from SpiceDB.
- `docs/how-to/manage-dynamic-soundscapes-and-audio-ducking.md` and `docs/how-to/project-campaign-analytics-and-chronicle-timeline.md` describe these routes. Update the auth text.
- Analytics builds its own database engine (`w3-ddd-architecture.md` F22). That is a DDD issue, not this task.

## Product & User Story References
- US-0040 (combat telemetry and living timeline). US-0054 (spatial heatmaps and damage analytics). US-0039 (encounter tension and foley). US-0053 (DM soundboard and foley triggers). PRD-0012 (telemetry and chronicle). PRD-0010 (soundscape).

## Detailed Specification & Implementation Plan
1. Campaign analytics:
   - `dependencies.py`: a missing subject returns 401. Remove the `return True` branch.
   - Read routes (MVP, heatmap, timeline) check `campaign.view`.
   - Delete the local `get_spicedb_client` and import the library factory.
2. Soundscape:
   - `check_user_can_control_soundscape`: require the verified principal. Missing returns 401. Check `session.control` on the session in the request, and `campaign.run_session` on the campaign when no session is given.
   - `cue`, `stems/override`, `override`, `stems/volume`, `duck`, `tension/calculate`: `session.control`.
   - Leitmotif configure and trigger: the character's `character.edit` or `session.control` (as the current code intends; keep the OR).
   - Delete the local factory and import the library factory.
3. Gateway forwarding is TASK-0536 (soundscape and analytics proxies). This task does not repeat it.
4. Proxy error behaviour is TASK-0536. Do not repeat it here.

## Frontdoor Blackbox Test Plan
Setup: a campaign, a session, a player, and a DM. Telemetry is produced by the public combat route (`campaign_analytics` read model is built from events through the public path).
- Before the fix, a gateway call to analytics with no principal returns 200. After the fix it returns 401.
- Soundscape `POST /api/v1/soundscape/duck` with no principal: 401. A player: 403. The DM: 200.
- Soundscape `POST /api/v1/soundscape/stems/volume` by a player: 403. Before the fix it returns 200.
- Soundscape `POST /api/v1/soundscape/tension/calculate` with no principal: 401.
- A stubbed SpiceDB outage returns 503 from the soundscape service.

## Definition of Done
1. Frontdoor tests exist in `tests/test_blackbox_analytics_soundscape_authz.py` and pass against the live harness.
2. `grep -rn "return True" services/soundscape/src/soundscape/dependencies.py services/campaign_analytics/src/campaign_analytics/dependencies.py` returns nothing on a no-identity path.
3. Both services use the library factory. No local factory remains.
4. The two how-to docs above are updated.
5. `uv run pytest services/soundscape services/campaign_analytics` passes. `uv run ruff check` passes for both.
6. No file in the change exceeds 500 lines.

## Audit Provenance

- Severity: high
- Source audits: `w2-campaign-analytics.md`, `w2-soundscape.md`, `w3-authz-coverage.md`
