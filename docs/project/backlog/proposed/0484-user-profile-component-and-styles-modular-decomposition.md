---
id: '0484'
title: User Profile Component and Styles Modular Decomposition
status: Proposed
created: 2026-09-29
dependencies:
- TASK-0257
- TASK-0357
governing_adrs:
- ADR-0004
- ADR-0012
- ADR-0013
governing_prds:
- PRD-0023
governing_stories:
- US-0063
- US-0068
target_release: 0.9.0
---

# TASK-0484: User Profile Component and Styles Modular Decomposition

## Status
Proposed

## Summary
Decompose `frontend/src/components/runefoble-user-profile.ts` (290 lines) into modular submodules under `frontend/src/components/profile/` (`profile.styles.ts`, `profile-details.ts`, `profile-security.ts`, and index/facade), ensuring all submodules remain strictly < 100 lines per Hard Invariant 6.

## Problem Statement
`frontend/src/components/runefoble-user-profile.ts` implements user identity profile display, email verification badge rendering, password/security claims, avatar thumbnail customization, and profile update forms in a single file alongside embedded CSS styling. As preferences for notifications, audio device selection, and custom token portraits are added to the user settings view, this component will rapidly breach the 500-line invariant limit unless decoupled into dedicated CSS style sheets and view templates.

## Governing Architecture & ADRs
- **ADR-0004: Lit Web Components and Storybook UI**: Partitioning Lit components into styles and templates while preserving CustomElement registration and Shadow DOM encapsulation.
- **ADR-0012: Design System Theming and Bauhaus Modernism**: High-contrast Bauhaus design tokens isolated in CSS custom properties.
- **ADR-0013: Frontend Microfrontend Architecture**: Clean modular structure within frontend component suites.

## Product & User Story References
- [`prd-0023-unified-frontend-application-shell-and-campaign-hub.md`](../../product/accepted/prd-0023-unified-frontend-application-shell-and-campaign-hub.md)
- [`us-0063-campaign-creation-dashboard-and-zanzibar-roles.md`](../../user_stories/accepted/us-0063-campaign-creation-dashboard-and-zanzibar-roles.md)
- [`us-0068-user-profile-and-account-settings.md`](../../user_stories/accepted/us-0068-user-profile-and-account-settings.md)

## Scope of Work
1. **Styles Extraction (`frontend/src/components/profile/runefoble-user-profile.styles.ts`)**:
   - Extract CSS templates into a dedicated styles module (< 80 lines).
2. **Form and Details Subviews (`frontend/src/components/profile/runefoble-user-profile.templates.ts`)**:
   - Extract account info fields, role badges, and editable form templates into focused helper renderers.
3. **Facade Component (`frontend/src/components/runefoble-user-profile.ts`)**:
   - Maintain the existing `<runefoble-user-profile>` custom element registration and public API contract as a slim coordinator strictly < 90 lines.
4. **Verification**:
   - Run `pnpm test` (or `npm test`) in `frontend/` and verify Storybook stories in `frontend/src/stories/runefoble-user-profile.stories.ts` continue to render without regression.

## Definition of Done
1. `frontend/src/components/runefoble-user-profile.ts` reduced to strictly < 90 lines.
2. All extracted submodules remain strictly < 100 lines per Hard Invariant 6.
3. 100% of frontend tests and Storybook component stories pass without regression.
