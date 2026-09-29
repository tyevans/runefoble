---
id: '0479'
title: Campaign Invites, Offline Recovery, and Audio Preflight Blackbox Test Suite
status: Proposed
created: 2026-09-29
dependencies:
- TASK-0475
- TASK-0476
- TASK-0477
- TASK-0478
governing_adrs:
- ADR-0001
- ADR-0004
- ADR-0007
- ADR-0014
governing_prds:
- PRD-0023
governing_stories:
- US-0063
- US-0065
- US-0066
- US-0071
target_release: 0.9.0
---

# TASK-0479: Campaign Invites, Offline Recovery, and Audio Preflight Blackbox Test Suite

## Status
Proposed

## Summary
Implement a comprehensive end-to-end blackbox test suite (`tests/test_blackbox_campaign_invites_and_preflight.py` and `frontend/test/campaign-invites-and-preflight.test.ts`) verifying invite link preview/join API frontdoors, SpiceDB Zanzibar access grants, client route transitions (`#/join/:inviteToken`), campaign archival status transitions, browser offline detection banner rendering, and microphone preflight WebAudio level calculation.

## Problem Statement
Hard Invariant 7 mandates that all feature development must be driven by blackbox tests interacting strictly through public frontdoors (HTTP routes, WebSockets, or published standard domain events) rather than reaching into private internals. To ensure that the newly proposed campaign invite flow (`TASK-0475`), offline status monitor (`TASK-0476`), audio preflight widget (`TASK-0477`), and campaign archival endpoints (`TASK-0478`) operate reliably without regressions, a dual-layer blackbox test suite (Python pytest for backend HTTP APIs and TypeScript vitest for Web Components and routing) is required.

## Governing Architecture & ADRs
- **ADR-0001: Google Zanzibar for Fine-Grained Authorization**: Asserting SpiceDB relationship creation upon invite redemption and permission checks on archive endpoints.
- **ADR-0004: Lit Web Components and Storybook UI**: Verifying component event contracts, Shadow DOM accessibility, and Bauhaus design token invariants.
- **ADR-0014: Behavior-Driven Development (BDD) with Playwright**: Aligning test fixtures with persona frontdoors (Evelyn, Marcus).

## Product & User Story References
- [`prd-0023-unified-frontend-application-shell-and-campaign-hub.md`](../../product/accepted/prd-0023-unified-frontend-application-shell-and-campaign-hub.md)
- [`us-0063-campaign-creation-dashboard-and-zanzibar-roles.md`](../../user_stories/accepted/us-0063-campaign-creation-dashboard-and-zanzibar-roles.md)
- [`us-0065-game-session-lobby-readiness-and-launch.md`](../../user_stories/accepted/us-0065-game-session-lobby-readiness-and-launch.md)
- [`us-0066-client-side-routing-navigation-and-breadcrumbs.md`](../../user_stories/accepted/us-0066-client-side-routing-navigation-and-breadcrumbs.md)
- [`us-0071-campaign-dashboard-idempotency-and-lifecycle.md`](../../user_stories/accepted/us-0071-campaign-dashboard-idempotency-and-lifecycle.md)

## Scope of Work
1. **Backend Blackbox API Test Suite (`tests/test_blackbox_campaign_invites_and_preflight.py`)**:
   - `test_invite_preview_returns_metadata_without_consuming_uses()`: Verify `GET /api/v1/campaigns/invites/{token}` returns 200 with campaign info and `is_valid: true`.
   - `test_invite_join_creates_zanzibar_relationship()`: Verify `POST /api/v1/campaigns/join` registers the user in SpiceDB Zanzibar and marks invite as used.
   - `test_campaign_archive_and_restore_lifecycle()`: Verify `POST /api/v1/campaigns/{id}/archive` and `/restore` enforce `manage` permission and update `status`.
   - `test_campaign_listing_filters_by_status()`: Verify `GET /api/v1/campaigns?status=archived` returns only archived items.
2. **Frontend Blackbox Component & Routing Suite (`frontend/test/campaign-invites-and-preflight.test.ts`)**:
   - `test_join_route_renders_campaign_join_card()`: Assert navigating to `#/join/test-token` renders `<runefoble-campaign-join-card>`.
   - `test_offline_status_banner_appears_on_network_loss()`: Trigger `window.dispatchEvent(new Event('offline'))` and assert `<runefoble-network-status>` displays warning.
   - `test_audio_preflight_component_emits_verification()`: Render `<runefoble-audio-preflight>`, mock media devices, and verify `@audio-check-completed` event payload.
3. **Hard Invariant 6 Compliance**:
   - Ensure all test files remain strictly < 300 lines.

## Definition of Done
1. Backend test suite passes via `uv run pytest tests/test_blackbox_campaign_invites_and_preflight.py`.
2. Frontend test suite passes via `npm test` or `pnpm test`.
3. 100% assertions interact strictly through public frontdoors.
4. All test files conform to Hard Invariant 6 (< 500 lines).
