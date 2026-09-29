---
id: '0436'
title: Gateway Soundscape API Routing & Zanzibar Authorization Proxy
status: Refined
created: 2026-09-28
dependencies:
- TASK-0050
- TASK-0109
- TASK-0352
governing_adrs:
- ADR-0001
- ADR-0006
- ADR-0010
- ADR-0013
governing_prds:
- PRD-0010
- PRD-0023
governing_stories:
- US-0039
- US-0053
- US-0065
target_release: 0.9.0
---

# TASK-0436: Gateway Soundscape API Routing & Zanzibar Authorization Proxy

## Status
Refined

## Summary
Implement a dedicated Gateway APIRouter (`gateway/api/src/gateway_api/routers/soundscape.py`) exposing `/api/v1/soundscape/*` endpoints (`/cue`, `/tension`, `/tension/calculate`, `/stems/override`, `/leitmotif`), protected by SpiceDB Zanzibar authorization checks (`play` or `run_session` permissions on session or campaign) and proxying downstream to the soundscape service (`http://soundscape:8010` / in-process fallback), enabling the `<runefoble-soundscape-controls>` microfrontend to interact with the soundscape backend through the gateway without 404 errors.

## Problem Statement
The dynamic soundscape service (`services/soundscape`) implements encounter tension calculations, stem mixing, manual DM mood overrides, and tactical foley cue triggers. However, the unified API Gateway (`gateway/api/src/gateway_api/main.py`) never includes soundscape routes. When the `<runefoble-soundscape-controls>` Lit component makes HTTP requests to `/api/v1/soundscape/cue` or `/api/v1/soundscape/stems/override`, the gateway returns 404 Not Found. Furthermore, there is no SpiceDB Zanzibar permission gating at the gateway edge to ensure only authorized players and DMs can trigger cues or override acoustic moods.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/how-to/manage-dynamic-soundscapes-and-audio-ducking.md`: Encounter tension, stem profiles, and cue triggering.
  - `docs/how-to/define-spicedb-zanzibar-permissions.md`: Zanzibar permissions `play` and `run_session` on `game_session` and `campaign`.
  - `docs/reference/ports-and-endpoints.md`: Soundscape service port 8010 and Gateway port 8000.
- **Governing Architecture & ADRs**:
  - **ADR-0001: Google Zanzibar for Fine-Grained Authorization**: Edge authorization enforcement via SpiceDB.
  - **ADR-0006: Redis Streams Distributed Domain Event Streaming**: Event publishing for audio mutations.
  - **ADR-0010: Real-Time Audio Pipeline and Ducking Coordination**: Soundscape controls and ducking coordination.
  - **ADR-0013: Frontend Microfrontend Architecture**: Gateway route aggregation for service microfrontends.

## Product & User Story References
- [`prd-0010-adaptive-soundscape-foley-and-tension-scoring.md`](../../product/accepted/prd-0010-adaptive-soundscape-foley-and-tension-scoring.md)
- [`prd-0023-unified-frontend-application-shell-and-campaign-hub.md`](../../product/accepted/prd-0023-unified-frontend-application-shell-and-campaign-hub.md)
- [`us-0039-encounter-tension-adaptive-scoring-and-foley.md`](../../user_stories/accepted/us-0039-encounter-tension-adaptive-scoring-and-foley.md)
- [`us-0053-dm-manual-soundboard-and-foley-triggers.md`](../../user_stories/accepted/us-0053-dm-manual-soundboard-and-foley-triggers.md)

## Detailed Specification & Implementation Plan
1. **Gateway Soundscape Router (`gateway/api/src/gateway_api/routers/soundscape.py`)**:
   - Define APIRouter with prefix `/api/v1/soundscape`, tags `["Soundscape"]`.
   - Forwarding endpoints:
     - `POST /cue`: Trigger a tactical foley cue (`SoundscapeCueRequest`). Zanzibar check: `play` permission on session or campaign.
     - `GET /tension`: Retrieve current tension and active stems. Public or authenticated.
     - `POST /tension/calculate`: Calculate encounter tension based on round/CR.
     - `POST /stems/override`: Manual DM mood/tension override. Zanzibar check: `run_session` or `manage` permission.
     - `GET /leitmotif/{character_id}`: Query character leitmotif timbre configuration.
   - Implement `SOUNDSCAPE_SERVICE_URL` proxy logic with in-process `soundscape` package fallback when running locally or in tests (< 130 lines).
2. **Mount Router on Gateway (`gateway/api/src/gateway_api/main.py`)**:
   - Import and include `soundscape_router` in `app.include_router(soundscape_router)`.
3. **Blackbox TDD Test Suite (`tests/test_blackbox_soundscape_gateway.py`)**:
   - Test `POST /api/v1/soundscape/cue` through the gateway with valid credentials.
   - Test `GET /api/v1/soundscape/tension` returning tension score and active stems.
   - Test `POST /api/v1/soundscape/stems/override` enforcing Zanzibar permissions.
   - Test 403 Forbidden when unauthorized user attempts to override mood.

## INVEST Criteria Evaluation
- **Independent (I)**: Addresses Gateway routing to soundscape service independently of UI rendering.
- **Negotiable (N)**: Fallback mock values and timeout configurations can be tuned.
- **Valuable (V)**: Unblocks `<runefoble-soundscape-controls>` from 404 errors and enforces security invariants.
- **Estimable (E)**: Standard FastAPI proxy router pattern already utilized in `character_subresources.py` and `downtime.py`.
- **Small (S)**: Confined to one new router file (< 130 lines), `main.py` include line, and one blackbox test file.
- **Testable (T)**: Frontdoor HTTP requests with `TestClient(app)` asserting 200 OK and 403 Forbidden.

## Definition of Done
1. `gateway/api/src/gateway_api/routers/soundscape.py` implemented (< 130 lines).
2. Gateway `app.include_router(soundscape_router)` mounted and exposed in `/openapi.json`.
3. SpiceDB Zanzibar permissions enforced on `/cue` and `/stems/override`.
4. Frontdoor blackbox test suite `tests/test_blackbox_soundscape_gateway.py` authored and 100% passing.
5. Code passes `uv run ruff check .` and `uv run ruff format --check .`.
