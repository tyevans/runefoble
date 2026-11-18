---
id: '0644'
title: Campaign Permissions Computed by the Gateway From SpiceDB Replace Client Role-Name Checks
status: Complete
created: 2026-11-17
dependencies: []
governing_adrs:
- ADR-0001
- ADR-0007
- ADR-0013
governing_prds:
- PRD-0023
governing_stories:
- US-0009
- US-0013
- US-0063
target_release: 0.9.0
---

# TASK-0644: Campaign Permissions Computed by the Gateway From SpiceDB Replace Client Role-Name Checks

## Status
Complete

## Summary
The App Shell decides who may manage a campaign, launch a session, or invite players by comparing role strings. `isDM` is `roles.some(r => ['dm','admin','owner'].includes(r))`. The campaign role is compared to `'owner'` and `'dm'`. Hard Invariant 1 forbids role checks in business logic. The gateway should return the per-campaign permissions that SpiceDB computes. The App Shell reads those flags and never compares role names. Server-side checks stay authoritative.

## Problem Statement
- `frontend/src/runefoble-app.ts:67-68` defines `isDM` from role names `dm`, `admin`, and `owner`.
- `frontend/src/runefoble-app.ts:220` and the campaign header compute `canManage` from `isDM` or `currentCampaign.role === 'owner' | 'dm'`. `canLaunch` and `isOwnerOrDm` follow the same pattern.
- `frontend/src/components/plugins/plugin_registry.ts:108` registers DM-only plugins by `isDm`.
- AGENTS.md Hard Invariant 1 requires permission checks against `libs/runefoble_auth/schema/runefoble.zed`.

## Documentation & Architecture Review
- `docs/how-to/define-spicedb-zanzibar-permissions.md` lists the permission names. Use those names. Do not invent new ones.
- `docs/how-to/manage-campaign-lifecycle-and-invites.md` describes the campaign roles. The response shape change must be documented there.
- ADR-0001: SpiceDB is the source of the flags. The gateway performs the lookup and returns booleans. It does not decide the rule itself.
- ADR-0007: campaign authorization belongs to the campaign bounded context's schema, not to the shell.

## Product & User Story References
- [`us-0009-zanzibar-campaign-access-control.md`](../../user_stories/accepted/us-0009-zanzibar-campaign-access-control.md)
- [`us-0013-gateway-zanzibar-authorization.md`](../../user_stories/accepted/us-0013-gateway-zanzibar-authorization.md)
- [`us-0063-campaign-creation-dashboard-and-zanzibar-roles.md`](../../user_stories/accepted/us-0063-campaign-creation-dashboard-and-zanzibar-roles.md)

## Detailed Specification & Implementation Plan
1. Define the permission set in `docs/reference/ports-and-endpoints.md` and in the response model: `permissions: { view, manage, invite, launch_session, assign_roles }`. Each is a boolean computed from SpiceDB `check` calls for the caller.
2. Gateway: `GET /api/v1/campaigns` and `GET /api/v1/campaigns/{id}` include the `permissions` object. Use the gateway's existing SpiceDB client. Do not add role comparisons.
3. App Shell: remove `isDM`, `canManage`, `canLaunch`, `isOwnerOrDm`, and every `role === 'owner' | 'dm'` comparison. Read `currentCampaign.permissions.*`. The `role` field may still be displayed as text.
4. Plugin registry: `plugin_registry.ts` filters DM-only plugins on `permissions.manage`, not `isDm`.
5. Remove the `admin` role string from the client entirely.
6. Keep server checks unchanged on every mutating route. The client flags only hide controls. They never grant access.

## Frontdoor Blackbox Test Plan
- Pytest (`tests/test_blackbox_campaign_permissions.py`): a player's `GET /api/v1/campaigns/{id}` returns `permissions.manage == false` and `launch_session == false`. A DM's response returns `true`. Both come from the public route.
- Playwright BDD (`e2e/features/campaign_permissions.feature` (not created)): a player opens a campaign and the "Launch session" control is not visible. The DM sees it. Setup uses the public campaign and role routes.
- Before the change the player's UI shows the controls based on `isDM` (for example, a player whose role string is `owner` in a stale token would see them). After the change the flags decide. The scenario asserts visibility from the server flags.

## Definition of Done
1. `grep -rn "'admin'\|'owner'\|role ===" frontend/src` returns no permission decision. Verified by a test that greps production sources.
2. The campaign list and detail responses include `permissions` and it is documented in `docs/reference/ports-and-endpoints.md`.
3. Pytest blackbox and Playwright BDD scenarios pass.
4. Mutating gateway routes still return 403 for unauthorised callers (existing tests stay green).
5. `pnpm run lint`, `pnpm test`, and `pnpm run build` pass.
6. Changelog entry under `[Unreleased]`.

## Audit Provenance

- Severity: medium
- Source audits: `w2-app-shell.md`
