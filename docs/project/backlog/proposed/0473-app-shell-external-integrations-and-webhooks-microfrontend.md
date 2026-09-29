---
id: '0473'
title: App Shell External Integrations and Webhook Management Microfrontend
status: Proposed
created: 2026-09-29
dependencies:
- TASK-0174
- TASK-0206
- TASK-0248
- TASK-0471
governing_adrs:
- ADR-0004
- ADR-0012
- ADR-0013
governing_prds:
- PRD-0022
- PRD-0023
governing_stories:
- US-0035
- US-0067
target_release: 0.9.0
---

# TASK-0473: App Shell External Integrations and Webhook Management Microfrontend

## Status
Proposed

## Summary
Implement an external integrations and webhook management subview in the App Shell campaign management interface (`frontend/src/components/campaign/integrations/runefoble-campaign-integrations.ts`). Provide Game Masters with intuitive UI controls to register outgoing webhooks (e.g. for Discord bots, stream alerts, or custom automation), select subscribed event types, view delivery status badges, inspect secret signing keys, and trigger instant test delivery pings.

## Problem Statement
While backend webhook routing and signing will exist via `TASK-0471`, Game Masters currently have no graphical interface to manage external webhooks or community bot connections. Without an integrated UI panel inside Campaign Settings, configuring webhooks requires manual API calls with curl or external HTTP clients, presenting a significant barrier for non-technical Game Masters and modders.

## Governing Architecture & ADRs
- **ADR-0004: Lit Web Components and Storybook UI**: Encapsulated Lit component with Bauhaus design tokens and Shadow DOM isolation.
- **ADR-0012: Design System Theming and Bauhaus Modernism**: Full inheritance of theme tokens (`--rf-color-*`, `--rf-space-*`) and light/dark mode compliance.
- **ADR-0013: Microfrontend Architecture & Service Component Vendoring**: Self-contained component decomposed into modular template, state, and styling sub-modules.

## Product & User Story References
- [`prd-0022-extensible-modder-platform-and-mcp-registry.md`](../../product/accepted/prd-0022-extensible-modder-platform-and-mcp-registry.md)
- [`prd-0023-unified-frontend-application-shell-and-campaign-hub.md`](../../product/accepted/prd-0023-unified-frontend-application-shell-and-campaign-hub.md)
- [`us-0035-runtime-mcp-tool-hot-reloading-and-extension-slots.md`](../../user_stories/accepted/us-0035-runtime-mcp-tool-hot-reloading-and-extension-slots.md)
- [`us-0067-campaign-detail-dashboard-and-tabbed-navigation.md`](../../user_stories/accepted/us-0067-campaign-detail-dashboard-and-tabbed-navigation.md)

## Scope of Work
1. **Integrations Component (`frontend/src/components/campaign/integrations/runefoble-campaign-integrations.ts`)**:
   - Custom element `<runefoble-campaign-integrations>` rendering list of configured webhooks with URL, status indicators, and event chips (< 140 lines).
2. **Webhook Creation & Test Modal (`frontend/src/components/campaign/integrations/webhook-dialog.ts`)**:
   - Modal for entering endpoint URL, selecting subscribed event categories (Combat, Dice, Chat, Presence), revealing generated HMAC signing secret, and executing a test ping (< 130 lines).
3. **Component Styles (`frontend/src/components/campaign/integrations/integrations-styles.ts`)**:
   - Scoped Bauhaus modernist CSS rules, responsive grid, status badges (Active, Failing, Pending) (< 110 lines).
4. **Storybook Stories (`frontend/src/stories/campaign-integrations.stories.ts`)**:
   - Interactive Storybook states: empty state, active webhooks list, delivery failure warning, and test ping feedback (< 120 lines).

## Definition of Done
1. `<runefoble-campaign-integrations>` implemented and integrated into Campaign Hub tabbed navigation.
2. Webhook modal enables creating, deleting, and testing external webhook configurations.
3. Component adheres to Bauhaus design system tokens with high-contrast accessibility.
4. All component source files strictly < 150 lines per Hard Invariant 6.
5. Storybook stories render without errors.
