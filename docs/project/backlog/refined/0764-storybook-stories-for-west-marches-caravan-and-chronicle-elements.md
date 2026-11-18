---
id: '0764'
title: Storybook Stories for West Marches, Caravan and Chronicle Elements
status: Refined
created: 2026-11-17
dependencies: []
governing_adrs:
- ADR-0004
- ADR-0013
governing_prds:
- PRD-0018
- PRD-0012
governing_stories:
- US-0004
target_bc: campaign_lore
target_release: 0.9.0
---
# TASK-0764: Storybook Stories for West Marches, Caravan and Chronicle Elements

## Status
Refined.

## Summary
Nine custom elements have no Storybook story. Add one story file each, co-located with the element. Hard Invariant 3 requires Storybook verification.

## Problem Statement
- `services/campaign_lore/ui/src/west_marches/`: `expedition_chronicle.ts`, `frontier_hex_overlay.ts`, `stronghold_dashboard_panel.ts`, `tavern_notice_board.ts`, `discovery_pin_layer.ts`.
- `services/campaign_analytics/ui/src/runefoble-chronicle-timeline.ts`.
- `services/game_session/ui/src/caravan/`: `contract_card.ts`, `dispatch_modal.ts`, `board_filters.ts`. Check first whether the caravan board story already renders them; if so, add a focused story only for states that story does not show.

## Documentation & Architecture Review
- ADR-0004, ADR-0013 point 5, `docs/how-to/develop-lit-components-in-storybook.md`. TASKs 0373, 0378, 0395, 0426, 0429 are Playwright BDD coverage and do not add stories.

## Product & User Story References
- PRD-0018, PRD-0012. US-0004.

## Detailed Specification & Implementation Plan
1. One `*.stories.ts` per element, with default, empty and error states, and one play function for its main event.
2. Stories use only public attributes and properties.

## Frontdoor Blackbox Test Plan
- `pnpm run build-storybook` succeeds. Each new story renders with zero console errors (Storybook test runner).

## Definition of Done
- Nine stories added. Storybook build clean. No file over 500 lines.

## Audit Provenance
- Severity: low
- Source audits: `frontend-ui`
