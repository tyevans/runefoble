---
id: 0248
title: Campaign Detail Hero Header and Metadata Component
status: Complete
created: 2026-09-27
dependencies:
- TASK-0210
- TASK-0220
governing_adrs:
- ADR-0001
- ADR-0004
- ADR-0012
- ADR-0013
governing_prds:
- PRD-0023
governing_stories:
- US-0063
- US-0067
target_release: 0.8.0
pr_url: https://github.com/tyevans/runefoble/pull/280
---
# TASK-0248: Campaign Detail Hero Header and Metadata Component

## Status
Refined

## Summary
Implement the `<runefoble-campaign-header>` Lit Web Component in `services/game_session/ui/src/campaigns/` providing a Bauhaus hero banner, campaign title, setting badge, system ruleset pill (e.g. 5e, PF2e), status indicator, narrative description, DM profile badge, and an "Edit Campaign" modal for users with SpiceDB Zanzibar `manage` permissions.

## Problem Statement
When visiting a campaign page (`#/campaigns/:id`), the user sees no header or campaign overview—only a member roster and session list placed abruptly in a grid layout. There is no visual presentation of the campaign's setting, ruleset, description, cover artwork, or DM information. Furthermore, Game Masters have no UI mechanism to edit campaign details (title, description, setting, system ruleset) after initial creation.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/reference/design-tokens-and-themes.md`: Bauhaus typography, border tokens, and surface color tokens.
  - `docs/how-to/develop-lit-components-in-storybook.md`: Lit component standards and Storybook story patterns.
  - `docs/how-to/define-spicedb-zanzibar-permissions.md`: Enforcing `manage` permission for editing campaign settings.
- **Governing Architecture & ADRs**:
  - **ADR-0001: SpiceDB Zanzibar Object Authorization**: Conditional rendering of GM controls based on Zanzibar `manage` permission.
  - **ADR-0004: Lit Web Components and Storybook UI**: Component encapsulation and Shadow DOM.
  - **ADR-0012: Design System Theming and Bauhaus Modernism**: High-contrast geometry and responsive layout tokens.
  - **ADR-0013: Microfrontend Architecture and Service Component Vendoring**: Vendored in `@runefoble/game-session-ui`.

## Product & User Story References
- **Product Requirement**: [`prd-0023-unified-frontend-application-shell-and-campaign-hub.md`](../../product/accepted/prd-0023-unified-frontend-application-shell-and-campaign-hub.md)
- **User Story**: [`us-0067-campaign-detail-view-and-session-scheduling.md`](../../user_stories/accepted/us-0067-campaign-detail-view-and-session-scheduling.md)

## Detailed Specification & Implementation Plan
1. **Campaign Header Web Component (`services/game_session/ui/src/campaigns/runefoble-campaign-header.ts`)**:
   - Properties: `campaign: CampaignItem | null`, `canManage: boolean`, `currentUserId: string`.
   - Hero banner displaying optional cover artwork with geometric Bauhaus fallback patterns.
   - Metadata badges: Ruleset System (`5e`, `PF2e`, `Call of Cthulhu`), Setting Name, Active Status pill, and DM avatar/username.
   - Narrative description section with readable line-height and typography tokens.
   - Action row: "Edit Campaign" button (visible only when `canManage` is true).
2. **Edit Campaign Modal**:
   - Modal dialog with form fields: Title, Setting, Ruleset System, Description, and Cover Image URL.
   - Dispatches custom event `@update-campaign` with `UpdateCampaignPayload` (`detail: { campaignId, ... }`).
3. **Storybook Stories (`services/game_session/ui/src/campaigns/runefoble-campaign-header.stories.ts`)**:
   - Story 1: `GameMasterView` (shows Edit Campaign button and full controls).
   - Story 2: `PlayerView` (read-only presentation without manage actions).
   - Story 3: `MinimalMetadata` (handles campaigns without cover images or long descriptions gracefully).
4. **Export and Manifest Registration**:
   - Export component in `services/game_session/ui/src/index.ts`.
   - Register custom element tag in `services/game_session/ui/manifest.json`.

## INVEST Criteria Evaluation
- **Independent (I)**: Self-contained Lit component testable in Storybook with fixture data.
- **Negotiable (N)**: Banner aspect ratios and tag badge placements can be adjusted for responsive breakpoints.
- **Valuable (V)**: Transforms the campaign detail page from a blank stub into an immersive fantasy campaign hub.
- **Estimable (E)**: Standard Lit presentation component and modal form sized for a single pass.
- **Small (S)**: Kept under 250 lines of component code, using modular CSS file if needed.
- **Testable (T)**: Frontdoor component tests verify edit modal dispatch and role-based button visibility.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. `<runefoble-campaign-header>` implemented in `services/game_session/ui/src/campaigns/`.
2. Storybook stories pass in all color modes with zero console warnings.
3. Component exported in `@runefoble/game-session-ui` and registered in `manifest.json`.
4. All source files strictly adhere to file length limit (<500 lines).
