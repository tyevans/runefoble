---
id: '0353'
title: Campaign Roster, Roles & Zanzibar Membership Lifecycle Integration
status: Complete
created: 2026-09-28
dependencies:
- TASK-0008
- TASK-0032
- TASK-0250
governing_adrs:
- ADR-0001
- ADR-0004
- ADR-0013
governing_prds:
- PRD-0023
governing_stories:
- US-0063
- US-0064
target_release: 0.9.0
pr_url: https://github.com/tyevans/runefoble/pull/352
---

# TASK-0353: Campaign Roster, Roles & Zanzibar Membership Lifecycle Integration

## Status
Complete

## Summary
Eradicate stubbed/identical campaign rosters by adding a Zanzibar-backed member removal endpoint (`DELETE /api/v1/campaigns/{id}/members/{user_id}`), enriching member responses with user and character profiles, wiring all `<runefoble-campaign-members>` custom events (`@assign-role`, `@create-invite`, `@remove-member`) in `frontend/src/runefoble-app.ts`, and implementing campaign-scoped fallback caching in `frontend/src/services/app-data-service.ts`.

## Problem Statement
When viewing any campaign (such as `camp-1790649479382`), the "Campaign Roster & Roles" panel displays the exact same static three members (`Valeros`, `Kyra`, `Merisiel`) because `app-data-service.ts` falls back to a global static fixture array (`FALLBACK_MEMBERS`) without campaign scoping. In `frontend/src/runefoble-app.ts`, `<runefoble-campaign-members>` is mounted with zero event listeners, meaning that attempting to change a member's role or remove a member drops the custom events silently. 

Furthermore, `AppDataService` contains no methods to assign roles, generate invites, or remove members. In the backend, `gateway/api/src/gateway_api/routers/campaigns.py` lacks an endpoint to remove a member from a campaign (`DELETE /api/v1/campaigns/{campaign_id}/members/{user_id}`), and `queries.py::get_campaign_members()` only queries raw SpiceDB Zanzibar relation tuples without resolving display names or linked characters.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/how-to/define-spicedb-zanzibar-permissions.md`: Writing and deleting SpiceDB Zanzibar relationship tuples.
  - `docs/how-to/manage-campaign-lifecycle-and-invites.md`: Campaign membership lifecycle, invite token generation, and role assignment.
  - `libs/runefoble_auth/schema/runefoble.zed`: `campaign` definition with relations `owner`, `dungeon_master`, `player`, `spectator`, and permission `manage`.
- **Governing Architecture & ADRs**:
  - **ADR-0001: Google Zanzibar for Fine-Grained Authorization**: SpiceDB schema enforcement and relationship management.
  - **ADR-0004: Lit Web Components and Storybook UI**: Component event contracts and shadow DOM encapsulation.
  - **ADR-0013: Frontend Microfrontend Architecture**: Bounded context composition and public frontdoor interfaces.

## Scope of Work & Implementation Plan
1. **Backend Gateway Member Removal Route (`gateway/api/src/gateway_api/routers/campaigns.py`)**:
   - Add `DELETE /api/v1/campaigns/{campaign_id}/members/{user_id}`:
     - Protected with Zanzibar dependency `require_zanzibar_permission("manage", "campaign", "campaign_id")`.
     - Read target user's existing relationships on `campaign:{campaign_id}` and invoke `spicedb.delete_relationship("campaign", campaign_id, rel, "user", user_id)`.
     - Return status response: `{"status": "member_removed", "campaign_id": campaign_id, "user_id": user_id}`.
2. **Backend Member Response Enrichment (`gateway/api/src/gateway_api/campaign_store/queries.py`)**:
   - Update `get_campaign_members()` to populate `username` and `character_name` by inspecting characters assigned to `campaign_id` owned by `user_id`.
3. **App Data Service Enhancements (`frontend/src/services/app-data-service.ts`)**:
   - Implement `assignMemberRole(campaignId: string, userId: string, role: string): Promise<void>`.
   - Implement `createCampaignInvite(campaignId: string, role: string, expiresInHours?: number, maxUses?: number): Promise<InviteResponse>`.
   - Implement `removeCampaignMember(campaignId: string, userId: string): Promise<void>`.
4. **Campaign-Scoped Fallback Cache (`frontend/src/services/app-data-service.fixtures.ts`)**:
   - Replace static `FALLBACK_MEMBERS` with `getFallbackCampaignMembers(campaignId: string)`.
   - Seed campaign `'4'` with Valeros, Kyra, and Merisiel.
   - Seed new campaigns with the creating user as Owner.
   - Implement `assignFallbackMemberRole()`, `removeFallbackMember()`, and `createFallbackInvite()` so offline/standalone mode fully functions.
5. **App Shell Event Wiring (`frontend/src/runefoble-app.ts`)**:
   - Bind `@assign-role=${(e: CustomEvent) => this.handleAssignRole(e)}`.
   - Bind `@create-invite=${(e: CustomEvent) => this.handleCreateInvite(e)}`.
   - Bind `@remove-member=${(e: CustomEvent) => this.handleRemoveMember(e)}`.
   - Supply `.inviteUrl` and `.inviteToken` dynamically from campaign state.
   - Provide toast notifications and reload `this.campaignMembers` on state change.
6. **Blackbox TDD Tests**:
   - Author `tests/test_blackbox_campaign_members_lifecycle.py` testing role assignment, invite token creation, and member removal via frontdoor HTTP endpoints.
   - Update `frontend/test/campaign-detail-view.test.ts` to assert member events and roster updates.

## INVEST Criteria Evaluation
- **Independent (I)**: Addresses campaign roster and role management independently of other campaign tabs.
- **Negotiable (N)**: Fallback member names and toast styling can be refined as needed.
- **Valuable (V)**: Eliminates stubbed rosters, enables functional player invites and role assignment, and enforces Zanzibar permissions.
- **Estimable (E)**: Straightforward REST and Lit event binding with existing component and schema.
- **Small (S)**: Confined to campaigns router, queries, AppDataService, and runefoble-app event handlers.
- **Testable (T)**: Directly testable via blackbox HTTP requests and frontend component interaction tests.

## Definition of Done
1. `DELETE /api/v1/campaigns/{campaign_id}/members/{user_id}` is implemented in gateway router and removes SpiceDB tuples.
2. `fetchCampaignMembers(campaignId)` returns distinct, campaign-scoped member lists rather than a single static list.
3. Assigning a role in `<runefoble-campaign-members>` persists via API or fallback cache and updates the UI without page reload.
4. Generating an invite creates a real token or scoped link, and removing a member removes them from the roster.
5. Blackbox test suite passes with 100% assertions.
