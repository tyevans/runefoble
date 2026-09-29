# How-To: Test User Flows with Playwright BDD

## Overview

Runefoble validates complete user flows and UI journeys spanning decoupled Lit Web Component microfrontends, SPA routing, Shadow DOM custom events, and backend microservices using **Playwright** (`@playwright/test`) and **Behavior-Driven Development (BDD)** via `playwright-bdd`.

Governed by **ADR-0014** and **Hard Invariant 7 (Blackbox TDD & BDD with Frontdoor Setup)**, every user-facing capability must have executable Gherkin feature files and automated browser tests that execute exclusively through public frontdoors with **zero backdoor state or database manipulation**.

---

## 1. Authoring Gherkin Features from User Stories

User stories in `docs/project/user_stories/accepted/` serve as the single source of truth for platform behavior. Translate user story acceptance criteria into Gherkin feature files under `e2e/features/`:

```gherkin
# e2e/features/campaign_management.feature
Feature: Campaign Creation and DM Dashboard
  As a Dungeon Master (DM)
  I want to create and manage campaigns through the public UI
  So that I can organize game sessions for my adventuring party

  Scenario: DM creates a new campaign through the creation modal
    Given I am logged in as a "DM"
    When I navigate to "#/campaigns"
    And I click the "New Campaign" button
    And I fill the campaign title with "The Sunless Citadel"
    And I click the "Create Campaign" button
    Then I should see the heading "The Sunless Citadel"
    And the URL hash should be "#/campaigns"
```

### Golden Rules for Scenarios
1. **Persona Grounding**: Start scenarios with explicit persona roles (`DM`, `Player`, `Spectator`).
2. **Declarative Intent**: Focus on what the user does and observes, not internal DOM classnames.
3. **Frontdoor Preconditions**: Every `Given` must describe a state achievable via public HTTP APIs, UI actions, or OIDC tokens.

---

## 2. Managing Frontdoor Test Setup and Authenticated Sessions

Hard Invariant 7 prohibits inserting rows directly into Postgres or manipulating internal aggregate stores. Setup must use public frontdoors:

### Authenticated Sessions via OIDC Injection
The authentication fixture (`e2e/support/auth_fixtures.ts`) synthesizes valid Zitadel JWTs and injects them into browser `localStorage` before page load:

```typescript
// e2e/steps/auth_steps.ts
import { Given } from '../support/fixtures';

Given('I am logged in as a {string}', async ({ auth, world }, roleOrName: string) => {
  const user = await auth.injectUser(roleOrName);
  world.currentUser = user;
});
```

Supported personas:
- `"DM"`: Dungeon Master credentials (`user-dm-eldrin`, roles `['dm', 'player']`).
- `"Player"`: Standard player credentials (`user-valeros`, role `['player']`).
- `"Spectator"`: Passive audience credentials (`user-spectator-zephyr`, role `['spectator']`).

### Entity Preconditions via Frontdoor API
To prepare prerequisites (e.g. existing campaigns, characters, or invites), use `frontdoorApi` (`e2e/support/frontdoor_api.ts`), which calls public REST endpoints:

```typescript
Given('campaign {string} exists', async ({ frontdoorApi, world }, campaignTitle: string) => {
  const token = world.currentUser?.token;
  const campaign = await frontdoorApi.createCampaign(campaignTitle, { token });
  world.campaignId = campaign.id;
  world.campaignTitle = campaign.title;
});
```

---

## 3. Implementing Step Definitions with Shadow-Piercing Locators

Runefoble components are Lit Web Components with Shadow DOM encapsulation. Playwright's locator engine automatically pierces open Shadow DOM roots without custom XPath hacks:

```typescript
// e2e/steps/campaign_steps.ts
import { expect } from '@playwright/test';
import { When, Then } from '../support/fixtures';

When('I fill the campaign title with {string}', async ({ page }, title: string) => {
  // Pierces Shadow DOM of runefoble-campaign-modal to locate the input
  const input = page.locator('runefoble-campaign-modal input[name="title"]');
  await input.fill(title);
});

When('I click the {string} button', async ({ page }, buttonName: string) => {
  // Resolves across Shadow DOM via accessible role or text match
  const button = page
    .getByRole('button', { name: buttonName })
    .or(page.locator(`button:has-text("${buttonName}")`))
    .first();
  await button.click();
});

Then('I should see the heading {string}', async ({ page }, headingText: string) => {
  const heading = page
    .getByRole('heading', { name: headingText })
    .or(page.locator('h1, h2, h3, h4').filter({ hasText: headingText }))
    .first();
  await expect(heading).toBeVisible({ timeout: 10_000 });
});
```

### Best Practices for Step Definitions
- **Use Web-First Assertions**: Always use `await expect(locator).toBeVisible()` or `expect.poll()` so Playwright auto-waits for async rendering and animations.
- **Query Composed Events**: When testing custom element events, assert observable DOM changes or public hash route updates rather than spying on private component methods.

---

## 4. Running and Debugging Tests Locally

The repository provides Makefile targets to execute and debug Playwright BDD suites:

### Validate Gherkin Syntax and Steps (Dry-Run)
Ensure all Gherkin steps in `e2e/features/` map to defined step definitions without launching browsers:
```bash
make test-bdd
```

### Run Headless E2E Test Suite
Run tests across Chromium, Firefox, and WebKit in headless mode:
```bash
make test-e2e
```

To run a specific browser or filter by scenario name:
```bash
make test-e2e ARGS="--project=chromium -g 'Dungeon Master'"
```

### Interactive UI Mode for Debugging
Launch the interactive Playwright UI mode with time-travel DOM inspection, step-by-step playback, and network logs:
```bash
make test-e2e-ui
```

---

## 5. BDD Governance Checklist for Engineers

Before submitting pull requests or considering a user-facing task "Done", verify:

- [ ] **DoR Met**: Governing user story in `docs/project/user_stories/accepted/` contains Gherkin scenarios with frontdoor-only setup.
- [ ] **Feature File Committed**: Feature file placed in `e2e/features/` with no private backdoors.
- [ ] **Step Definitions Implemented**: Step definitions in `e2e/steps/` use shadow-piercing locators and web-first assertions.
- [ ] **Cross-Browser Verification**: `make test-e2e` passes across Chromium, Firefox, and WebKit.
- [ ] **Zero Backdoor Manipulation**: Preconditions created solely through public REST APIs or OIDC session injection.
