---
id: '0590'
title: Campaign Lifecycle, Membership, and Invites Owned by Game Session
status: Refined
created: 2026-11-17
dependencies:
- TASK-0560
- TASK-0625
governing_adrs:
- ADR-0001
- ADR-0007
- ADR-0011
governing_prds:
- PRD-0023
- PRD-0018
governing_stories:
- US-0063
- US-0071
- US-0009
severity: critical
source_audits:
- w1-game-session.md
- w1-gateway-api.md
- w3-ddd-architecture.md
target_release: 0.9.0
---

# TASK-0590: Campaign Lifecycle, Membership, and Invites Owned by Game Session

## Status
Refined

## Summary
Campaign records, membership, invites and campaign sessions live in `gateway/api/src/gateway_api/campaign_store/` as in-memory dicts. A restart loses them. No bounded context owns them. This task makes `game_session` the owner. It adds eventsource-py aggregates and public routes for each operation. TASK-0591 then moves the gateway to proxy them.

**Decision required (see index report):** no ADR or doc assigns campaigns to a bounded context. This task uses `game_session` because it already holds the `game_session#campaign` relation in `libs/runefoble_auth/schema/runefoble.zed:35-41` and the `campaign_id` on sessions. If the owner decides a new campaign BC is needed, this task must be re-scoped first.

## Problem Statement
- `campaign_store/store.py:22-31` holds `_campaigns`, `_invites` and `_campaign_sessions` as `dict` objects (`w1-game-session.md` F2, `w1-gateway-api.md` F11).
- `campaign_store/invites.py:59-66` changes invite `uses` in place.
- `routers/campaigns.py:43-55` writes SpiceDB tuples before the in-memory record exists. The tuples outlive a gateway restart (`w1-gateway-api.md` F6, `w3-ddd-architecture.md` F6).
- `frontend/src/services/app-data-service.ts` calls `/campaigns/{id}/sessions` and `/sessions/{id}`. Those routes map to the gateway store, not to the game-session aggregate (`w1-game-session.md` F2).
- Two session entities exist: gateway campaign sessions and game-session aggregates. No link joins them (`w1-game-session.md` F8).
- `docs/how-to/manage-campaign-lifecycle-and-invites.md` documents the public contract. Keep the contract.

## Documentation & Architecture Review
- ADR-0011 (eventsource-py): every state change uses a `DeclarativeAggregate` with `@handles` methods, saved through `AggregateRepository`. Each command emits an event that inherits from `BaseRunefobleEvent` and is registered with `@register_event`.
- ADR-0001: each membership change writes or deletes the matching SpiceDB tuple. The write happens in the owner, after the aggregate save succeeds.
- TASK-0560 makes the PostgreSQL event store mandatory for `game_session`. This task depends on it. Without it, campaign data is still lost on restart.
- Permission names come from `libs/runefoble_auth/schema/runefoble.zed`. Do not add a role check in code.

## Product & User Story References
- [`prd-0023-unified-frontend-application-shell-and-campaign-hub.md`](../../product/accepted/prd-0023-unified-frontend-application-shell-and-campaign-hub.md)
- [`us-0063-campaign-creation-dashboard-and-zanzibar-roles.md`](../../user_stories/accepted/us-0063-campaign-creation-dashboard-and-zanzibar-roles.md)
- [`us-0071-campaign-dashboard-idempotency-and-lifecycle.md`](../../user_stories/accepted/us-0071-campaign-dashboard-idempotency-and-lifecycle.md)
- [`us-0009-zanzibar-campaign-access-control.md`](../../user_stories/accepted/us-0009-zanzibar-campaign-access-control.md)

## Detailed Specification & Implementation Plan
1. Add a `campaign` package under `services/game_session/src/game_session/campaign/`. Use one file per aggregate (each under 300 lines):
   - `campaign_aggregate.py`: create, update settings, set status. Events: `CampaignCreated`, `CampaignUpdated`.
   - `membership_aggregate.py`: add member with role, remove member. Events: `CampaignMemberAdded`, `CampaignMemberRemoved`.
   - `invite_aggregate.py`: create invite (role, expiry, max uses), redeem (check expiry and uses). Events: `CampaignInviteCreated`, `CampaignInviteRedeemed`.
   - `campaign_session_aggregate.py`: create staging session for a campaign. Event: `CampaignSessionCreated`.
2. Register the events in `libs/runefoble_events` with `@register_event`. Do not put event classes in `game_session`.
3. Add public routes under `/api/v1/campaigns` in `game_session`, with the same paths and bodies as the gateway today (see `docs/how-to/manage-campaign-lifecycle-and-invites.md`):
   - `GET /api/v1/campaigns` (only campaigns the caller can `view`; use the SpiceDB lookup helper from `runefoble_auth`).
   - `POST /api/v1/campaigns`, `GET`/`PATCH /api/v1/campaigns/{id}`.
   - `POST /api/v1/campaigns/{id}/invites`, `POST /api/v1/campaigns/join`.
   - `GET /api/v1/campaigns/{id}/members`, `DELETE /api/v1/campaigns/{id}/members/{user_id}`.
   - `GET`/`POST /api/v1/campaigns/{id}/sessions`.
4. Membership writes: after each saved membership event, write or delete the SpiceDB relation through the shared SpiceDB factory from TASK-0625.
5. The role-assignment route `POST /api/v1/campaigns/{id}/roles` is not moved here. Its missing authorization is owned by the authorization theme. Record the dependency in the PR. TASK-0591 must not ship the gateway route without that fix.
6. Add the Helm env needed for the aggregates. Confirm TASK-0560 sets the PostgreSQL store flag for `game_session`.

## Frontdoor Blackbox Test Plan
Test file: `tests/test_blackbox_campaign_lifecycle_owner.py`. `game_session` runs as an ASGI app. Setup goes only through public routes (create, invite, join).

| Case | Expected before fix | Expected after fix |
|---|---|---|
| Campaign created, then the app restarts, then `GET /api/v1/campaigns/{id}` returns it | Fails: no owner | Passes (event store reload) |
| Invite with `max_uses: 1` accepts one join and rejects the second with 409 | Fails: no owner | Passes |
| Expired invite returns 410 or the owner's documented code | Fails: no owner | Passes |
| Member removed loses `GET /members` entry and SpiceDB `view` | Fails: no owner | Passes |
| `GET /api/v1/campaigns` omits campaigns the caller cannot view | Fails: no owner | Passes |

## Definition of Done
1. Four aggregates and their events exist. Each file is under 300 lines.
2. Each route in step 3 is in the OpenAPI schema of `game_session`.
3. Membership and invite state survives a restart with the PostgreSQL store.
4. SpiceDB tuples are written only after the aggregate save succeeds. A test covers a failed save.
5. The blackbox test file passes. `uv run ruff check .` passes.
6. `docs/how-to/manage-campaign-lifecycle-and-invites.md` and `docs/reference/ports-and-endpoints.md` name `game_session` as the owner.
