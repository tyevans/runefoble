---
id: '0646'
title: Embedded Analytics and Lore Microfrontends Receive Live Data From the Gateway
status: Complete
created: 2026-11-17
dependencies: []
governing_adrs:
- ADR-0004
- ADR-0007
- ADR-0013
governing_prds:
- PRD-0007
- PRD-0012
- PRD-0023
governing_stories:
- US-0040
- US-0050
- US-0054
target_release: 0.9.0
severity: high
source_audits:
- w2-campaign-analytics.md
- w2-campaign-lore.md
---

# TASK-0646: Embedded Analytics and Lore Microfrontends Receive Live Data From the Gateway

## Status
Complete

## Summary
Two campaign tabs mount microfrontends that never show real data. The "Chronicle & Stats" tab passes `apiBaseUrl=""`, so the analytics component returns before it fetches anything. The "Codex & Lore" tab mounts `runefoble-campaign-atlas` with no pins, territories, or entries, and it never mounts `runefoble-campaign-codex`. Pass the gateway base, load the atlas and codex data through the gateway, and mount the codex view.

## Problem Statement
- `frontend/src/runefoble-app.ts:220` renders `<runefoble-campaign-analytics .campaignId=... apiBaseUrl="">`. `services/campaign_analytics/ui/src/runefoble-campaign-analytics.ts:37` and `:54` return before any `fetch` when `apiBaseUrl` is empty. The tab stays empty.
- `frontend/src/runefoble-app.ts:220` (the codex tab) renders `<runefoble-campaign-atlas .campaignId .isGm .isDM>` with no data. `runefoble-campaign-codex` is never mounted (`w2-campaign-lore.md` F15).
- Both defects make the tabs look live while showing nothing.

## Documentation & Architecture Review
- `docs/how-to/project-campaign-analytics-and-chronicle-timeline.md` describes the analytics endpoints (`/api/v1/analytics/campaigns/{id}/heatmap|mvp|timeline`). The shell must call the gateway routes that exist, and the docs must name them.
- `docs/how-to/interact-with-campaign-atlas-and-codex.md` describes the atlas and codex. Update it with the data source.
- ADR-0013: components fetch through a base URL passed by the shell, or resolve it from the gateway origin. They do not call service ports directly.

## Product & User Story References
- [`us-0040-campaign-combat-telemetry-and-living-timeline.md`](../../user_stories/accepted/us-0040-campaign-combat-telemetry-and-living-timeline.md)
- [`us-0054-combat-spatial-heatmaps-and-party-damage-analytics.md`](../../user_stories/accepted/us-0054-combat-spatial-heatmaps-and-party-damage-analytics.md)
- [`us-0050-collaborative-campaign-atlas-and-living-codex.md`](../../user_stories/accepted/us-0050-collaborative-campaign-atlas-and-living-codex.md)
- [`prd-0012-campaign-telemetry-and-living-chronicle-timeline.md`](../../product/accepted/prd-0012-campaign-telemetry-and-living-chronicle-timeline.md)

## Detailed Specification & Implementation Plan
1. Analytics tab: pass the gateway origin (for example `apiBaseUrl="/api/v1/analytics"` or the same-origin base) from one constant in `app-data-service.ts`. Remove the `apiBaseUrl=""` literal.
2. Analytics component: the empty-base early return becomes a typed error state, not a silent no-op. Confirm that the three endpoints (heatmap, MVP, timeline) return data for a seeded session through the public routes.
3. Codex tab: mount `runefoble-campaign-codex` for the codex view and `runefoble-campaign-atlas` for the atlas view. Use two sub-tabs so that both exist. Pass `campaign-id`, `is-gm`, and the permissions from TASK-0644.
4. Atlas and codex load their data from the gateway routes in `gateway/api` (campaign-lore routes). Where a route does not exist, the task adds a thin gateway proxy with Zanzibar checks, in its own router file.
5. Empty datasets show an empty state, not sample pins.
6. Keep each component file under 500 lines. The App Shell change is only the tab wiring.

## Frontdoor Blackbox Test Plan
Playwright BDD (`e2e/features/campaign_analytics_and_codex.feature`):
- Scenario: The Chronicle & Stats tab shows a milestone.
  - Given a campaign with a session where a combat event was recorded through the public session routes
  - When the DM opens the Chronicle & Stats tab
  - Then the tab shows the milestone title from the timeline endpoint.
- Scenario: A pin created through the atlas UI appears in the codex view.
  - When the DM places a pin "Star-Eater Gate" in the atlas
  - Then the codex sub-tab lists "Star-Eater Gate".
- Before the change both scenarios FAIL (empty tabs). After the change they PASS.
- Pytest (`tests/test_blackbox_analytics_timeline_frontdoor.py`) confirms the timeline route returns the seeded milestone.

## Definition of Done
1. `grep -rn 'apiBaseUrl=""' frontend/src` returns no match.
2. The codex view mounts `runefoble-campaign-codex`. Verified by the BDD scenario.
3. Both BDD scenarios pass in all three browsers, with setup through public routes only.
4. Docs in the two how-to guides name the gateway routes used.
5. Storybook stories for the analytics and atlas components build with zero console errors.
6. `pnpm run build` passes. Changelog entry under `[Unreleased]`.
