# How-To: Test User Flows with Playwright BDD

## Overview

Use this guide to write a Gherkin user flow and its step definitions. Each scenario runs in a real browser through Playwright (`@playwright/test`) and `playwright-bdd`.

Governed by **ADR-0014** and **Hard Invariant 7 (Blackbox TDD & BDD with Frontdoor Setup)**. Every scenario sets up its data through public frontdoors. No step writes to a database or to internal service state.

For the harness itself (fixtures, persona table, Makefile targets and CI job), read [E2E Harness reference](../reference/e2e-harness.md).

---

## 1. Author Gherkin Features from User Stories

User stories in `docs/project/user_stories/accepted/` define the acceptance criteria. Write each scenario under `e2e/features/`:

```gherkin
# e2e/features/campaign_hub.feature
Feature: Campaign Hub

  Scenario: DM opens the campaign hub
    Given I am logged in as a "DM"
    When I navigate to "#/campaigns"
    Then I should see the heading "Campaigns"
    And the URL hash should be "#/campaigns"
```

### Golden Rules for Scenarios
1. **Persona Grounding**: Start each scenario with an explicit persona (`DM`, `Player`, or a named persona from the [persona table](../reference/e2e-harness.md#global-setup-and-personas)).
2. **Declarative Intent**: Describe what the user does and sees. Do not describe CSS classes or DOM structure.
3. **Frontdoor Preconditions**: Every `Given` must reach its state through UI actions, public REST routes or an OIDC session.

---

## 2. Set Up Preconditions Through Frontdoors

### Log In a Persona
The step `I am logged in as a {string}` signs the persona in through Zitadel. The first sign-in of a persona in a worker completes the hosted login page, as a real user does. Later scenarios in the same worker reuse that session. The suite never forges a token. The step is defined in `e2e/steps/common_steps.ts`:

```gherkin
Given I am logged in as a "DM"
```

### Create Entities Through the Frontdoor API
The step `campaign {string} exists` creates a campaign through `POST /api/v1/campaigns`. It is defined in `e2e/steps/common_steps.ts`:

```typescript
Given('campaign {string} exists', async ({ frontdoorApi, world }, campaignTitle: string) => {
  const token = world.currentUser?.token;
  const campaign = await frontdoorApi.createCampaign(campaignTitle, { token });
  world.campaignId = campaign.id;
  world.campaignTitle = campaign.title;
});
```

```gherkin
Given I am logged in as a "DM"
And campaign "The Sunless Citadel" exists
```

### Setup Rules
- A setup step must throw when its request fails.
- A setup step must not fall back to a fixed id.
- A step must not call a database, a private store or a test-only route.

---

## 3. Write Step Definitions with Shadow-Piercing Locators

Runefoble components are Lit Web Components with Shadow DOM. Playwright locators pierce open shadow roots, so a step does not need custom XPath.

The step `I click the {string} button` resolves a button by role, text or `aria-label`. It is defined in `e2e/steps/common_steps.ts`:

```typescript
When('I click the {string} button', async ({ page }, buttonName: string) => {
  const button = page
    .getByRole('button', { name: buttonName })
    .or(page.locator(`button:has-text("${buttonName}")`))
    .or(page.locator(`[aria-label="${buttonName}"]`))
    .first();
  await button.click();
});
```

### Best Practices for Step Definitions
- **Use Web-First Assertions**: Use `await expect(locator).toBeVisible()` or `expect.poll()`. Playwright then waits for async rendering.
- **Assert Observable Output**: Check the DOM, the URL hash or a public projection. Do not spy on private component methods.
- **Act Through Visible Controls**: A step clicks or types through a control the user sees. Do not set a component field, dispatch a synthetic `CustomEvent`, write `data-theme`, or set `window.location.hash` to skip a flow. A step that cannot find its control must fail. Governed by ADR-0014 and Hard Invariant 7.

Correct pattern, from `e2e/steps/vtt_steps.ts`: launch the session through the DM's button, then drag, then assert the result on the board.

```typescript
const launchBtn = evelynPage.locator('runefoble-session-lobby .btn-launch').first();
await expect(launchBtn, 'Launch control must be visible to the DM').toBeVisible({ timeout: 10_000 });
await launchBtn.click();
```

Incorrect pattern. Do not write this:

```typescript
// Wrong: writes private component state and skips the launch flow.
await page.evaluate(() => {
  const app = document.querySelector('runefoble-app') as any;
  app.campaignMembers = [...app.campaignMembers, { username: 'Thorin' }];
});
```
- **Read the Base URL From Config**: Never write a host such as `http://localhost:5173` in a step. Use `test.info().project.use.baseURL`.
- **Fail on Missing Setup**: A setup step that cannot create its data must throw.

---

## 4. Run Multi-Browser Scenarios

Use one browser context for each persona that acts at the same time. Create the context from the project base URL:

```typescript
const context = await browser.newContext({ baseURL: test.info().project.use.baseURL });
world.extraContexts.push(context);
const page = await context.newPage();
await auth.signInAs('valeros', page);
world.setPage('valeros', page);
```

`World` closes every context in `world.extraContexts` after the scenario. The steps in `e2e/steps/vtt_steps.ts` show the pattern for a session lobby. The step `Evelyn is hosting session {string} for campaign {string}` opens the first page. The step `Valeros joins {string} in a separate browser` opens a second context.

### Personas

Global setup creates the personas in Zitadel before the suite runs. See the [E2E Harness reference](../reference/e2e-harness.md#global-setup-and-personas) for the table. The step name ignores case and punctuation:

| Name in step | Persona key |
|---|---|
| `DM`, `Dungeon Master`, `GM`, `master` | `dm` |
| `Player` | `player` |
| `Evelyn`, `Valeros`, `Sarah`, `Marcus` | The persona with that name |

A name that matches no persona fails the step. Add a new persona to `PERSONA_KEYS` in `e2e/support/personas.ts`. Do not add a fallback.

The step `I am logged in as a {string}` in `e2e/steps/common_steps.ts` accepts any of these names.

---|---|
| `evelyn` | Evelyn, the DM who hosts sessions |
| `valeros` | Valeros, a player |
| `sarah` | Sarah, a player |
| `dm`, `master`, or `gm` | The DM persona (`gm` is an alias) |
| `spectator` | A spectator |
| any other name | The default player persona |

The step `I am logged in as a {string}` in `e2e/steps/common_steps.ts` accepts any of these names.

---

## 5. Run and Debug

Use these commands from the repository root. The reference page lists what each command runs.

```bash
make test-bdd      # Typecheck, unused-step check and Gherkin mapping. No browsers.
make test-e2e      # Full suite in Chromium, Firefox and WebKit, against the running Kind stack.
make test-e2e-ui   # Playwright UI mode for debugging.

# Both e2e targets read the Zitadel admin token from the cluster. Start the Kind stack first.
```

To run one browser or one scenario, pass `ARGS`:

```bash
make test-e2e ARGS="--project=chromium -g 'Dungeon Master'"
```

---

## 6. BDD Governance Checklist

Before you submit a pull request or mark a user-facing task Done, verify:

- [ ] **DoR Met**: The governing user story in `docs/project/user_stories/accepted/` has Gherkin scenarios with frontdoor-only setup.
- [ ] **Feature File Committed**: The feature file is in `e2e/features/`.
- [ ] **Steps Implemented**: Every step is defined in `e2e/steps/`. Locators pierce shadow roots. Assertions are web-first.
- [ ] **Unused Steps Removed**: `make test-bdd` passes.
- [ ] **Cross-Browser Verification**: `make test-e2e` passes in Chromium, Firefox and WebKit.
- [ ] **Zero Backdoor Manipulation**: Preconditions use only public REST routes or OIDC session injection.
