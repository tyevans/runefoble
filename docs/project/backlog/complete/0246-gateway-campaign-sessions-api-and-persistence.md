---
id: '0246'
title: Gateway Campaign Sessions API and Persistence
status: Complete
created: 2026-09-27
dependencies:
- TASK-0208
- TASK-0221
governing_adrs:
- ADR-0001
- ADR-0005
- ADR-0007
governing_prds:
- PRD-0023
governing_stories:
- US-0063
- US-0067
target_release: 0.8.0
pr_url: https://github.com/tyevans/runefoble/pull/282
---
# TASK-0246: Gateway Campaign Sessions API and Persistence

## Status
Refined

## Summary
Extend `gateway/api/src/gateway_api/routers/campaigns.py` and `gateway_api/campaign_store/` with REST endpoints and in-memory persistence for campaign sessions: `GET /api/v1/campaigns/{campaign_id}/sessions` (list sessions with `view` permission) and `POST /api/v1/campaigns/{campaign_id}/sessions` (create session/staging lobby with `run_session` permission).

## Problem Statement
The frontend session list (`<runefoble-session-list>`) and campaign view currently make requests to `GET /api/v1/campaigns/{campaign_id}/sessions`, but the Gateway API returns HTTP 404 because no session listing or session creation routes exist under `/api/v1/campaigns/{campaign_id}`. Furthermore, creating a new session from the UI currently navigates to an invalid mock `/lobby/new` route without creating a persistent session record in the backend store or checking SpiceDB Zanzibar `run_session` permissions.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/how-to/define-spicedb-zanzibar-permissions.md`: Schema relations for `run_session` on campaigns.
  - `docs/how-to/manage-campaign-lifecycle-and-invites.md`: Campaign REST API patterns and Zanzibar integration.
  - `docs/reference/ports-and-endpoints.md`: Gateway routing table and microservice ports.
- **Governing Architecture & ADRs**:
  - **ADR-0001: SpiceDB Zanzibar Object Authorization**: Enforcing `view` relation to read sessions and `run_session` relation to create sessions.
  - **ADR-0005: Kubernetes-First Infrastructure with Helm and Kind**: FastAPI gateway service.
  - **ADR-0007: Domain-Driven Design Architecture**: Gateway API orchestrating session boundaries.

## Product & User Story References
- **Product Requirement**: [`prd-0023-unified-frontend-application-shell-and-campaign-hub.md`](../../product/accepted/prd-0023-unified-frontend-application-shell-and-campaign-hub.md)
- **User Stories**:
  - [`us-0063-campaign-creation-dashboard-and-zanzibar-roles.md`](../../user_stories/accepted/us-0063-campaign-creation-dashboard-and-zanzibar-roles.md)
  - [`us-0067-campaign-detail-view-and-session-scheduling.md`](../../user_stories/accepted/us-0067-campaign-detail-view-and-session-scheduling.md)

## Detailed Specification & Implementation Plan
1. **Pydantic Models (`gateway/api/src/gateway_api/models.py`)**:
   - `CreateCampaignSessionRequest`: `title: str`, `scheduled_at: str | None = None`, `description: str = ""`, `status: str = "lobby"` (`lobby` or `upcoming`).
   - `CampaignSessionResponse`: `id: str`, `campaign_id: str`, `title: str`, `status: str`, `round: int = 1`, `participants_count: int = 0`, `scheduled_at: str | None = None`, `created_at: str`.
2. **Campaign Store Session Methods (`gateway/api/src/gateway_api/campaign_store/store.py`)**:
   - Extend `CampaignStore` to manage sessions associated with campaigns (`_campaign_sessions: dict[str, list[CampaignSessionRecord]]`).
   - `create_session(campaign_id: str, title: str, status: str, ...)` generating unique session IDs (`session-<uuid>`).
   - `get_campaign_sessions(campaign_id: str)` returning all active, upcoming, and lobby sessions.
3. **Gateway Router Endpoints (`gateway/api/src/gateway_api/routers/campaigns.py`)**:
   - `GET /api/v1/campaigns/{campaign_id}/sessions`: Validate Zanzibar `view` permission on campaign, return list of `CampaignSessionResponse`.
   - `POST /api/v1/campaigns/{campaign_id}/sessions`: Validate Zanzibar `run_session` permission on campaign, create session record, return HTTP 201 Created.
4. **Blackbox HTTP Tests (`tests/test_blackbox_gateway_campaign_sessions.py`)**:
   - Verify non-members cannot list campaign sessions (403 Forbidden).
   - Verify members with `player` role can list sessions but cannot create sessions (403 Forbidden on POST).
   - Verify campaign owners/DMs with `run_session` permission can create sessions and list them.

## INVEST Criteria Evaluation
- **Independent (I)**: Operates independently within gateway router, testable via standard FastAPI TestClient.
- **Negotiable (N)**: Session status lifecycle states (`upcoming`, `lobby`, `active`, `completed`) can be extended.
- **Valuable (V)**: Unblocks the frontend session list from relying on static fallback fixtures and enables dynamic session scheduling.
- **Estimable (E)**: Pure FastAPI APIRouter and in-memory store methods sized within a single pass.
- **Small (S)**: File additions kept under 200 lines to preserve router file limit (<350 lines).
- **Testable (T)**: Frontdoor HTTP blackbox tests verify session creation, listing, and SpiceDB Zanzibar authorization checks.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. `GET` and `POST` `/api/v1/campaigns/{campaign_id}/sessions` implemented in `gateway/api/src/gateway_api/routers/campaigns.py`.
2. SpiceDB Zanzibar permissions enforced via `require_zanzibar_permission`.
3. Blackbox frontdoor tests in `tests/test_blackbox_gateway_campaign_sessions.py` pass.
4. All modified files strictly adhere to file length limit (<500 lines).
