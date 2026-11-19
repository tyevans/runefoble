---
id: '0624'
title: Helm Wiring for Service URL Environment Variables and Remove Localhost Defaults
status: Complete
created: 2026-11-17
dependencies:
- TASK-0622
governing_adrs:
- ADR-0005
- ADR-0007
governing_prds:
- PRD-0001
governing_stories:
- US-0007
target_release: 0.9.0
---

# TASK-0624: Helm Wiring for Service URL Environment Variables and Remove Localhost Defaults

## Status
Complete

## Summary
Cross-service URLs are read from environment variables that the Helm chart never sets. In the cluster, voice-agent falls back to `localhost:8001`, game-session never calls The Watcher, the-watcher never calls the inference worker, and gateway proxies use defaults that do not match the chart. Set every service URL in the chart from values, and replace code defaults that point at `localhost` or a wrong port.

## Problem Statement
- `RUNEFOBLE_WATCHER_URL` is read at `services/game_session/src/game_session/dependencies.py:30` (removed) (None means autopilot skips The Watcher, `routers/autopilot.py:79`). `services/voice_agent/src/voice_agent/dependencies.py:19` and `stt.py:108` default to `http://localhost:8001`. No Helm key sets it (`w1-gates-infra.md` F2).
- `RUNEFOBLE_INFERENCE_URL` is read at `services/the_watcher/src/the_watcher/dependencies.py:28`; not set in Helm (`w1-the-watcher.md` F2).
- Gateway: `SOUNDSCAPE_SERVICE_URL` (`routers/soundscape.py:21`, default port 8010 which is audience-studio; soundscape listens on 8009), `CAMPAIGN_LORE_URL`, `CAMPAIGN_ANALYTICS_URL` (`routers/hub_views.py:12-13`), and `CHARACTER_SHEET_URL` (`routers/character_subresources.py:26`, no default) are not set in `deployments/` (`w1-gateway-api.md` F14, F15).
- Campaign analytics `CAMPAIGN_ANALYTICS_URL` default is correct (8011); it is only unset in Helm.

## Documentation & Architecture Review
- `docs/reference/ports-and-endpoints.md` is the port source of truth (soundscape 8009). Add the new env keys to the platform services reference.
- ADR-0005: keys are rendered from `values.yaml` through the existing templates.
- The soundscape proxy behaviour itself is owned by TASK-0436; this task only sets the URL and corrects the code default. TASK-0436 must be corrected to use 8009 (see the index report).

## Product & User Story References
- PRD-0001, US-0007 in `docs/project/product/accepted/` and `docs/project/user_stories/accepted/`.

## Detailed Specification & Implementation Plan
1. Add a `serviceUrls` block to `values.yaml` built from the existing `services.*.port` values (no new literals), for example `theWatcher: http://the-watcher:8001`, `inferenceWorker: http://inference-worker:8100`, `soundscape: http://soundscape:8009`, `campaignLore: http://campaign-lore:8006`, `campaignAnalytics: http://campaign-analytics:8011`, `characterSheet: http://character-sheet:8003`.
2. Render these into the containers that need them:
   - game-session and voice-agent: `RUNEFOBLE_WATCHER_URL`.
   - the-watcher: `RUNEFOBLE_INFERENCE_URL` (only when `inferenceWorker` is enabled).
   - gateway-api: `SOUNDSCAPE_SERVICE_URL`, `CAMPAIGN_LORE_URL`, `CAMPAIGN_ANALYTICS_URL`, `CHARACTER_SHEET_URL`.
3. In code, change `voice_agent` defaults from `http://localhost:8001` to a required value (fail at startup when unset in non-dev mode) or to `http://the-watcher:8001`. Choose one and document it.
4. In `gateway/api/src/gateway_api/routers/soundscape.py`, change the default from `http://soundscape:8010` to `http://soundscape:8009`.
5. Add a Helm render test that asserts each key above is present on the matching container.

## Frontdoor Blackbox Test Plan
- Before fix: `helm template ... | grep RUNEFOBLE_WATCHER_URL` returns nothing. Through the running stack, a game-session autopilot request reports "watcher not configured" path (no Watcher call).
- After fix: rendered Deployments contain every key with the expected URL. A pytest module (`tests/test_blackbox_helm_service_urls.py`) renders the chart and checks the keys. Through HTTP, `POST /api/v1/soundscape/tension` through the gateway reaches the soundscape service (verified by a response that is not a fallback payload; see TASK-0436).

## Definition of Done
1. All listed keys render from values, with no `localhost` default left in service code paths that run in-cluster.
2. The soundscape default is 8009 in code and docs.
3. Helm lint and template pass.
4. `docs/reference/platform-services.md` lists each key.
5. No file above 500 lines.

## Audit Provenance

- Severity: high
- Source audits: `w1-gates-infra.md`, `w1-gateway-api.md`, `w1-the-watcher.md`, `w2-voice-agent.md`, `w2-campaign-analytics.md`, `w2-soundscape.md`
