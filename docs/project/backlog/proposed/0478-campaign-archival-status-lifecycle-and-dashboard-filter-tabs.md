---
id: '0478'
title: Campaign Archival Status Lifecycle and Dashboard Archive Filter Tabs
status: Proposed
created: 2026-09-29
dependencies:
- TASK-0208
- TASK-0209
- TASK-0250
governing_adrs:
- ADR-0001
- ADR-0004
- ADR-0010
- ADR-0013
governing_prds:
- PRD-0023
governing_stories:
- US-0063
- US-0071
target_release: 0.9.0
---

# TASK-0478: Campaign Archival Status Lifecycle and Dashboard Archive Filter Tabs

## Status
Proposed

## Summary
Add a campaign status lifecycle (`active` | `archived` | `completed`) to the backend campaign store, introduce archive/restore endpoints (`POST /api/v1/campaigns/{id}/archive` and `POST /api/v1/campaigns/{id}/restore`), and update `<runefoble-campaign-dashboard>` with status filter tabs ("Active", "Archived", "All") to enable Game Masters to archive completed campaigns and declutter their primary hub.

## Problem Statement
In PRD-0023 Section 2 and US-0071, Game Masters need a clutter-free campaign hub where concluded or inactive campaigns can be archived without deleting their underlying chronicles, session histories, or SpiceDB permission tuples. Currently, `CampaignRecord` in `gateway/api/src/gateway_api/campaign_store/` does not store a `status` field, and the Gateway API lacks any status transition endpoints. In `<runefoble-campaign-dashboard>`, users only have role filters ("All", "DMing", "Playing"), meaning that every completed campaign ever created remains permanently visible in the active grid.

## Governing Architecture & ADRs
- **ADR-0001: Google Zanzibar for Fine-Grained Authorization**: Enforcing `manage` permission via SpiceDB Zanzibar before allowing archival or restoration.
- **ADR-0004: Lit Web Components and Storybook UI**: Adding Bauhaus status pill tabs to `<runefoble-campaign-dashboard>` with accessible aria-selected semantics.
- **ADR-0010: Eventsource Aggregate Pattern**: Emitting standard domain events (`CampaignArchived`, `CampaignRestored`) when status changes.
- **ADR-0013: Frontend Microfrontend Architecture**: Preserving modular separation between dashboard presentation and gateway persistence.

## Product & User Story References
- [`prd-0023-unified-frontend-application-shell-and-campaign-hub.md`](../../product/accepted/prd-0023-unified-frontend-application-shell-and-campaign-hub.md)
- [`us-0063-campaign-creation-dashboard-and-zanzibar-roles.md`](../../user_stories/accepted/us-0063-campaign-creation-dashboard-and-zanzibar-roles.md)
- [`us-0071-campaign-dashboard-idempotency-and-lifecycle.md`](../../user_stories/accepted/us-0071-campaign-dashboard-idempotency-and-lifecycle.md)

## Scope of Work
1. **Backend Model & API Endpoints (`gateway/api/src/gateway_api/routers/campaigns.py` & `campaign_store/`)**:
   - Add `status: Literal['active', 'archived', 'completed'] = 'active'` to `CampaignRecord` and `CampaignResponse`.
   - Add `POST /api/v1/campaigns/{id}/archive`:
     - Checks `manage` permission on `campaign:{id}`.
     - Updates status to `'archived'` and updates `updated_at`.
   - Add `POST /api/v1/campaigns/{id}/restore`:
     - Checks `manage` permission and sets status back to `'active'`.
   - Support optional `?status=active|archived|all` query parameter on `GET /api/v1/campaigns`.
2. **Dashboard Status Tabs & Archive Action (`services/game_session/ui/src/campaigns/runefoble-campaign-dashboard.ts`)**:
   - Add status filter tab strip ("Active" default, "Archived", "All").
   - Add "Archive Campaign" menu action on campaign cards for campaigns where user is Owner/DM.
   - For archived campaigns, show a muted visual treatment and a "Restore" button.
   - Dispatch `@archive-campaign` and `@restore-campaign` custom events.
3. **App Shell & Data Service Integration (`frontend/src/runefoble-app.ts` & `frontend/src/services/app-data-service.ts`)**:
   - Implement `archiveCampaign(id)` and `restoreCampaign(id)` methods with fallback fixture support.
   - Update `runefoble-app.ts` event handlers to call the service and refresh campaign list with toast feedback.

## Definition of Done
1. `GET /api/v1/campaigns` filters by status and defaults to active campaigns.
2. `POST /api/v1/campaigns/{id}/archive` and `POST /api/v1/campaigns/{id}/restore` require Zanzibar `manage` permission and update status.
3. `<runefoble-campaign-dashboard>` renders status tabs and handles archive/restore events.
4. Storybook stories cover active, archived, and empty dashboard states.
5. All source files conform to Hard Invariant 6 (< 500 lines per file).
