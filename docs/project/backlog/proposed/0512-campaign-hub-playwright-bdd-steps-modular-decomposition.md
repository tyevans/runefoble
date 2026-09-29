---
id: '0512'
title: Campaign Hub Playwright BDD Steps Modular Decomposition
status: Proposed
created: 2026-09-29
dependencies:
- TASK-0361
governing_adrs:
- ADR-0003
- ADR-0004
- ADR-0010
- ADR-0013
- ADR-0014
governing_prds:
- PRD-0023
governing_stories:
- US-0062
- US-0063
- US-0064
- US-0066
- US-0067
target_release: 0.9.0
---

# TASK-0512: Campaign Hub Playwright BDD Steps Modular Decomposition

## Status
Proposed

## Summary
Decompose `e2e/steps/campaign_hub_steps.ts` (446 lines, 89.2% of 500-line invariant limit) into modular, single-responsibility step definition files under `e2e/steps/campaign_hub/` (`common.ts`, `campaign_creation_steps.ts`, `member_roles_steps.ts`, `navigation_tabs_steps.ts`), keeping all submodules strictly < 150 lines per Hard Invariant 6 and ADR-0013.

## Problem Statement
`e2e/steps/campaign_hub_steps.ts` implements end-to-end Playwright BDD user journeys for campaign creation, SpiceDB Zanzibar member role assignments, invite code/link generation and clipboard copying, and tab transitions across Overview, Party, Codex, and Chronicle in a single 446-line file. Approaching the hard 500-line limit per AGENTS.md Rule 6, adding upcoming BDD scenarios (such as campaign archival tabs, invite acceptance links, or settlement town navigation) will breach the hard line invariant unless modularized into focused submodules.

## Governing Architecture & ADRs
- **ADR-0003: Continuous Architecture & Modular Refactoring**: Proactively decomposing files approaching the 500-line invariant.
- **ADR-0004: Lit Web Components and Storybook UI**: Custom element shadow-piercing locators and event dispatches.
- **ADR-0010: Continuous Integration Pipeline**: Rapid test runs with Playwright BDD test runner.
- **ADR-0013: Modular Decomposition**: All source files kept strictly < 500 lines (submodules < 150 lines).
- **ADR-0014: Behavior-Driven Development (BDD) with Playwright and Cucumber**: Frontdoor BDD scenario step definitions without database manipulation.

## Product & User Story References
- Technical debt refactoring supporting:
  - [`prd-0023-unified-frontend-application-shell-and-campaign-hub.md`](../../product/accepted/prd-0023-unified-frontend-application-shell-and-campaign-hub.md)
  - [`us-0062-user-registration-zitadel-auth-and-profile.md`](../../user_stories/accepted/us-0062-user-registration-zitadel-auth-and-profile.md)
  - [`us-0063-campaign-creation-dashboard-and-zanzibar-roles.md`](../../user_stories/accepted/us-0063-campaign-creation-dashboard-and-zanzibar-roles.md)
  - [`us-0064-character-roster-and-party-assignment.md`](../../user_stories/accepted/us-0064-character-roster-and-party-assignment.md)
  - [`us-0066-client-side-routing-navigation-and-breadcrumbs.md`](../../user_stories/accepted/us-0066-client-side-routing-navigation-and-breadcrumbs.md)
  - [`us-0067-campaign-detail-view-and-session-scheduling.md`](../../user_stories/accepted/us-0067-campaign-detail-view-and-session-scheduling.md)

## Scope of Work
1. **Shared Fixtures & Helpers (`e2e/steps/campaign_hub/common.ts`)**:
   - Extract `ensureOnCampaignOverview` and common navigation/selector utilities (< 60 lines).
2. **Campaign Creation Steps (`e2e/steps/campaign_hub/campaign_creation_steps.ts`)**:
   - Extract campaign creation wizard steps, title/setting/ruleset inputs, and dashboard card assertions (< 100 lines).
3. **Member Management & Zanzibar Roles (`e2e/steps/campaign_hub/member_roles_steps.ts`)**:
   - Extract invite creation, clipboard copy validation, role assignment (Owner, DM, Player, Spectator), and member removal steps (< 120 lines).
4. **Navigation Tabs & Breadcrumb Steps (`e2e/steps/campaign_hub/navigation_tabs_steps.ts`)**:
   - Extract tab switching between Overview, Party Characters, Codex, and Analytics, verifying zero dead ends and active breadcrumb state (< 120 lines).
5. **Step Aggregator (`e2e/steps/campaign_hub_steps.ts`)**:
   - Re-export submodules or maintain clean index delegation to prevent breaking Cucumber step registry (< 30 lines).
6. **Verification**:
   - Run Playwright BDD test suite asserting 100% passing scenarios with zero line count violations.

## Definition of Done
1. `e2e/steps/campaign_hub_steps.ts` decomposed into `e2e/steps/campaign_hub/` submodules strictly < 150 lines each.
2. All campaign hub BDD feature scenarios pass with 100% assertions.
3. Code passes `pnpm lint` and TypeScript typechecks.
