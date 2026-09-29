---
id: '0361'
title: Campaign Hub Lifecycle and Navigation Playwright BDD Test Suite
status: Complete
created: 2026-09-28
dependencies:
- TASK-0353
- TASK-0354
- TASK-0355
- TASK-0359
governing_adrs:
- ADR-0001
- ADR-0004
- ADR-0013
- ADR-0014
governing_prds:
- PRD-0023
governing_stories:
- US-0050
- US-0063
- US-0064
- US-0067
target_release: 0.9.0
pr_url: https://github.com/tyevans/runefoble/pull/375
---
# TASK-0361: Campaign Hub Lifecycle and Navigation Playwright BDD Test Suite

## Status
Refined

## Summary
Implement a comprehensive, frontdoor-driven Playwright BDD test suite (`e2e/features/campaign_hub.feature`) verifying the complete Campaign Hub lifecycle per ADR-0014. Automate end-to-end user journeys for campaign creation, SpiceDB Zanzibar member role assignments, invite link generation and copying, session scheduling, and tab transitions across Overview, Party Characters, Codex & Lore, and Chronicle & Stats.

## Problem Statement
The Campaign Hub (`#/campaigns/:campaignId`) is the central organizing space for game masters and players. Historically, integration regressions—including identical static rosters, hardcoded session lists, and unclickable tabs with `e.preventDefault()`—passed through backend unit tests because no browser-level tests exercised the user interface end-to-end. 

To ensure the Campaign Hub remains completely functional, free of mock fallbacks, and resilient against regressions, we must implement automated Playwright BDD scenarios executing user flows strictly through public browser interactions.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/how-to/manage-campaign-lifecycle-and-invites.md`: Campaign creation, shareable invite tokens, and Zanzibar member roles.
  - `docs/how-to/navigate-client-spa-routes-and-breadcrumbs.md`: SPA hash navigation and breadcrumbs.
  - `docs/how-to/interact-with-campaign-atlas-and-codex.md`: Campaign atlas and lore codex.
  - `docs/how-to/project-campaign-analytics-and-chronicle-timeline.md`: Combat telemetry and chronicle timeline.
- **Governing Architecture & ADRs**:
  - **ADR-0001: Google Zanzibar for Fine-Grained Authorization**: SpiceDB object permissions.
  - **ADR-0004: Lit Web Components and Storybook UI**: Shadow DOM components.
  - **ADR-0013: Microfrontend Architecture and Service Component Vendoring**: Microfrontend boundaries.
  - **ADR-0014: Behavior-Driven Development (BDD) with Gherkin User Stories and Playwright End-to-End Validation**: BDD testing framework.

## Scope of Work & Implementation Plan
1. **Gherkin Feature Specification (`e2e/features/campaign_hub.feature`)**:
   - **Scenario 1: Creating a New Campaign as a Game Master**:
     - `Given Evelyn is logged in as a Dungeon Master`
     - `When she clicks "+ New Campaign" and fills in title "Wrath of the Lich King" and setting "Northrend"`
     - `Then a new campaign should be created and navigation transitions to "#/campaigns/:id"`
     - `And she should be displayed in the Campaign Roster as "Owner"`.
   - **Scenario 2: Managing Campaign Roster & SpiceDB Zanzibar Roles**:
     - `Given a campaign exists with members "Marcus" and "Sarah"`
     - `When Evelyn changes Marcus's role from "Player" to "Dungeon Master"`
     - `Then a toast notification "Role updated" appears`
     - `And Marcus's role dropdown shows "Dungeon Master"`.
   - **Scenario 3: Generating and Copying Campaign Invites**:
     - `When Evelyn clicks "Invite Adventurers", selects role "Player", and clicks "Generate Link"`
     - `Then a shareable invite link containing a signed token is displayed`
     - `And clicking "Copy Link" copies the valid join URL to the clipboard`.
   - **Scenario 4: Navigating Campaign Tabs Without Dead Ends**:
     - `When Evelyn clicks "Party Characters", the URL hash becomes "#/campaigns/:id/characters"`
     - `When Evelyn clicks "Codex & Lore", the URL hash becomes "#/campaigns/:id/codex" and `<runefoble-campaign-atlas>` renders`
     - `When Evelyn clicks "Chronicle & Stats", the URL hash becomes "#/campaigns/:id/analytics" and `<runefoble-campaign-analytics>` renders`
     - `When Evelyn clicks "Overview & Sessions", the URL hash returns to "#/campaigns/:id"`.
2. **Step Definitions Implementation (`e2e/steps/campaign_hub_steps.ts`)**:
   - Implement shadow-piercing Playwright locators for `<runefoble-campaign-header>`, `<runefoble-campaign-members>`, `<runefoble-campaign-creator>`, and `<nav class="campaign-nav-tabs">`.
   - Enforce frontdoor setup using `FrontdoorApi.createCampaign()` or UI interactions.
3. **Execution & CI Integration**:
   - Ensure `make test-e2e` executes `campaign_hub.feature` against live Vite and Gateway instances with zero failures.

## INVEST Criteria Evaluation
- **Independent (I)**: Focuses on the Campaign Hub lifecycle and can execute independently in test environments.
- **Negotiable (N)**: Scenario step phrases can be refined to match accepted user stories.
- **Valuable (V)**: Directly guarantees that Campaign Roster, Sessions, Codex, and Analytics tabs remain operational and un-stubbed.
- **Estimable (E)**: Clearly defined UI paths and Gherkin scenarios.
- **Small (S)**: Feature file and TypeScript step definition module (< 250 lines).
- **Testable (T)**: Directly executable via Playwright with deterministic assertions.

## Definition of Done
1. `e2e/features/campaign_hub.feature` covers campaign creation, roster roles, invite generation, and all 4 navigation tabs.
2. All step definitions interact strictly through public frontdoors (UI elements and public REST endpoints).
3. Playwright test suite passes across Chromium, Firefox, and WebKit.
4. No source or test file exceeds 500 lines per Hard Invariant 6.
