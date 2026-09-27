---
id: '0208'
title: Gateway Campaign Lifecycle and Membership API
status: Refined
created: 2026-09-27
dependencies: []
governing_adrs:
- ADR-0001
- ADR-0005
- ADR-0007
governing_prds:
- PRD-0023
governing_stories:
- US-0063
target_release: 0.8.0
---

# TASK-0208: Gateway Campaign Lifecycle and Membership API

## Status
Refined

## Summary
Extend `gateway/api/src/gateway_api/routers/campaigns.py` to support full campaign lifecycle management: listing campaigns for the authenticated user, creating new campaigns with automatic SpiceDB Zanzibar ownership tuples, generating shareable invite tokens, and joining campaigns.

## Problem Statement
The gateway currently only provides read proxying for single hardcoded campaigns (`GET /api/v1/campaigns/{id}`) and assigning roles (`POST /api/v1/campaigns/{id}/roles`). There are no endpoints to list all campaigns belonging to a user, create a new campaign, generate invite links, or accept invites.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/how-to/define-spicedb-zanzibar-permissions.md`: Schema relations in `runefoble.zed`, relationship writes, and permission checks.
  - `docs/reference/ports-and-endpoints.md`: Gateway routing table and microservice ports.
- **Governing Architecture & ADRs**:
  - **ADR-0001: SpiceDB Zanzibar Object Authorization**: Enforcing campaign ownership and membership relations (`campaign:X#owner@user:Y`, `campaign:X#player@user:Z`).
  - **ADR-0005: Kubernetes-First Infrastructure with Helm and Kind**: Zitadel JWT authentication.
  - **ADR-0007: Domain-Driven Design Architecture**: Gateway as API orchestration layer.

## Product & User Story References
- **Product Requirement**: [`prd-0023-unified-frontend-application-shell-and-campaign-hub.md`](../../product/accepted/prd-0023-unified-frontend-application-shell-and-campaign-hub.md)
- **User Story**: [`us-0063-campaign-creation-dashboard-and-zanzibar-roles.md`](../../user_stories/accepted/us-0063-campaign-creation-dashboard-and-zanzibar-roles.md)

## Detailed Specification & Implementation Plan
1. **Campaign CRUD Endpoints (`gateway/api/src/gateway_api/routers/campaigns.py`)**:
   - `GET /api/v1/campaigns`: Return all campaigns where the user has `view` permission (filtered by SpiceDB lookup or user metadata).
   - `POST /api/v1/campaigns`: Create a new campaign, writing `campaign:{id}#owner@user:{user_id}` relation to SpiceDB.
   - `PATCH /api/v1/campaigns/{campaign_id}`: Update campaign title, description, and settings (requires `manage` permission).
2. **Campaign Invites and Membership**:
   - `POST /api/v1/campaigns/{campaign_id}/invites`: Generate cryptographically signed or stored invite tokens with role designation (`player`, `spectator`).
   - `POST /api/v1/campaigns/join`: Accept an invite token and register membership in SpiceDB Zanzibar.
   - `GET /api/v1/campaigns/{campaign_id}/members`: List all members and their active Zanzibar roles.
3. **Pydantic Models (`gateway/api/src/gateway_api/models.py`)**:
   - `CreateCampaignRequest`, `CampaignSummaryResponse`, `InviteRequest`, `JoinCampaignRequest`, `CampaignMemberResponse`.

## INVEST Criteria Evaluation
- **Independent (I)**: Exposes standard REST endpoints callable by any HTTP client, decoupled from frontend UI release.
- **Negotiable (N)**: Invite token TTL and role mapping can be customized.
- **Valuable (V)**: Enables true multi-campaign creation and player joining with strict Zanzibar isolation.
- **Estimable (E)**: Standard FastAPI APIRouter and SpiceDB gRPC writes sized within a single pass.
- **Small (S)**: Router additions kept under 200 lines to preserve router file limit (<350 lines).
- **Testable (T)**: Frontdoor HTTP blackbox tests verify campaign creation, invite code exchange, and role verification.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. Endpoints implemented in `gateway/api/src/gateway_api/routers/campaigns.py` (<350 lines).
2. Pydantic models for campaign creation, invites, and member lists defined in `gateway/api/src/gateway_api/models.py`.
3. Automated blackbox tests verify campaign creation and membership retrieval with zero backdoor manipulation.
4. Passes `uv run pytest tests/test_blackbox_gateway_campaigns.py` and `uv run ruff check gateway/api/`.
