---
id: '0488'
title: Remove Backward Compatibility Shims & Re-exports in gateway_api
status: Refined
created: 2026-09-29
dependencies:
- TASK-0045
- TASK-0352
governing_adrs:
- ADR-0001
- ADR-0002
- ADR-0010
- ADR-0013
governing_prds:
- PRD-0001
- PRD-0023
governing_stories:
- US-0010
- US-0065
target_release: 0.9.0
---

# TASK-0488: Remove Backward Compatibility Shims & Re-exports in gateway_api

## Status
Refined

## Summary
Excise all backward-compatible facades, alias files, and camelCase request field shims from `gateway/api` (`webrtc_signaling.py`, `websocket.py`, `mobile_companion.py`, `websocket_manager.py` aliases, and `campaign_store/__init__.py`), migrate all callers directly to authoritative submodules, and eliminate facade parity tests.

## Problem Statement
During past refactorings in `gateway/api`, several facade modules were retained in `gateway/api/src/gateway_api/` (`webrtc_signaling.py`, `websocket.py`, `mobile_companion.py`, and `campaign_store/__init__.py`), re-exporting symbols for backward compatibility. In addition, `websocket_manager.py` contains `CampaignWebSocketManager = WebSocketManager` alias aliases, and router schemas retain redundant camelCase aliases (e.g., `alias="playerId"`, `alias="displayName"`). Because there are no live external users, these shims add technical debt and violate DoR rule 9.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/reference/ports-and-endpoints.md`: Gateway port 8000 and router endpoints.
  - `docs/how-to/authenticate-with-zitadel-oidc.md`: Gateway security and authentication.
- **Governing Architecture & ADRs**:
  - **ADR-0001: Google Zanzibar for Fine-Grained Authorization**: Edge authorization in Gateway.
  - **ADR-0010: Real-Time Audio Pipeline and WebSockets**: Live event streaming.
  - **ADR-0013: Frontend Microfrontend Architecture**: Gateway route aggregation.

## Product & User Story References
- [`prd-0001-runefoble-platform-foundations.md`](../../product/accepted/prd-0001-runefoble-platform-foundations.md)
- [`prd-0023-unified-frontend-application-shell-and-campaign-hub.md`](../../product/accepted/prd-0023-unified-frontend-application-shell-and-campaign-hub.md)
- [`us-0010-developer-local-infrastructure-and-test-tooling.md`](../../user_stories/accepted/us-0010-developer-local-infrastructure-and-test-tooling.md)

## Detailed Specification & Implementation Plan
1. **Delete Facade Modules**:
   - Delete `gateway/api/src/gateway_api/webrtc_signaling.py` (callers must import from `gateway_api.signaling.*`).
   - Delete `gateway/api/src/gateway_api/websocket.py` (callers must import from `gateway_api.websocket.*`).
   - Delete `gateway/api/src/gateway_api/mobile_companion.py` (callers must import from `gateway_api.companion.*`).
2. **Clean Up Aliases and Legacy Re-exports**:
   - In `gateway/api/src/gateway_api/websocket_manager.py`, remove `# Backward-compatible aliases` (`CampaignWebSocketManager`).
   - In `gateway/api/src/gateway_api/campaign_store/__init__.py`, eliminate facade re-exports, standardizing direct imports from submodules.
   - In `gateway/api/src/gateway_api/routers/tabletop.py` and `routers/auth/profile.py`, remove redundant legacy field aliases where canonical snake_case is expected.
3. **Migrate Import Sites Across Codebase**:
   - Update `gateway/api/src/gateway_api/main.py`, sub-routers, and tests to import directly from modular sub-packages (`gateway_api.signaling`, `gateway_api.websocket`, `gateway_api.companion`).
4. **Update Blackbox Test Suites**:
   - In `tests/test_blackbox_webrtc_auth.py`, remove `test_signaling_facade_and_submodule_backward_compatibility()`.
   - In `tests/test_websocket_modular_decomposition.py`, remove facade parity assertions.

## INVEST Criteria Evaluation
- **Independent (I)**: Changes are isolated to `gateway/api` and direct API test suites.
- **Negotiable (N)**: Clean standard FastAPI routing and Pydantic field conventions.
- **Valuable (V)**: Streamlines Gateway routing architecture and removes 3 facade modules.
- **Estimable (E)**: Clearly bounded to 4 facade files and specific alias definitions.
- **Small (S)**: File changes conform strictly to the < 500 lines invariant.
- **Testable (T)**: Verified via `uv run pytest tests/test_blackbox_*gateway*` and `tests/test_websocket*.py`.

## Definition of Done
1. `webrtc_signaling.py`, `websocket.py`, and `mobile_companion.py` deleted from `gateway/api`.
2. Aliases removed from `websocket_manager.py` and `campaign_store/__init__.py`.
3. Call sites across Gateway and tests migrated to authoritative submodules.
4. Obsolete facade parity tests removed.
5. All Gateway tests pass cleanly and `make lint` succeeds.
