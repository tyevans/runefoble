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

### Setup Rules (Fail Loud)
- A setup step must throw when its request fails. The error must hold the response status and body.
- A setup step must not fall back to a fixed id or title. Store the value that the setup call returns in `world`.
- A later step reads that value through `requireValue` from `e2e/support/guards.ts`. A missing value fails the step.
- `world.getPage(name)` throws when no step opened a page for that persona. Do not substitute another persona's page.
- A step must not call a database, a private store or a test-only route.

Correct pattern. The setup call throws on failure, and the id comes from its reply:

```typescript
const token = requireValue(world.currentUser?.token, 'No access token. Sign Evelyn in before campaign setup.');
const camp = await frontdoorApi.createCampaign('Wrath of the Lich King', { setting: 'Northrend', token });
world.campaignId = requireValue(camp.id, 'The campaign reply has no id.');
```

Incorrect pattern. Do not write this:

```typescript
// Wrong: a failed precondition lets the scenario run on a campaign that may not exist.
try {
  world.campaignId = (await frontdoorApi.createCampaign(title, { token })).id;
} catch {
  world.campaignId = '4';
}
```

`make test-bdd` runs the unit tests of these guards (`e2e/unit/guards.test.ts`) with `node --test`.

### Create the Campaign and Session in the Background
Each feature file creates its own data in its `Background`. A scenario never uses data from another scenario or from a seeded database. Names in feature text are labels only. Do not write an id in feature text, and do not derive an id from a name.

Do these steps in the Background, in this order:

1. Sign in the DM. The DM creates the campaign through `POST /api/v1/campaigns`.
2. The DM creates the session through `POST /api/v1/campaigns/{campaign_id}/sessions` (`frontdoorApi.createCampaignSession`).
3. For each player, the DM issues an invite (`createCampaignInvite`). The player redeems it (`joinCampaign`).
4. Each player creates a character (`createCharacter`). Do not send `level`. The character service does not keep it at creation.
5. Each player takes a seat through `POST /api/v1/sessions/{session_id}/join` (`frontdoorApi.joinSession`).
6. Store each id from the replies in `world`.

`e2e/features/session_lobby_and_vtt.feature` and `e2e/steps/vtt_setup_steps.ts` show the pattern:

```gherkin
Background:
  Given Evelyn creates campaign "Lobby Campaign" with session "Lobby 15" through the gateway
  And Valeros and Sarah redeem a player invite to the campaign in separate browsers
  And Valeros takes a seat in "Lobby 15" with a new character "Valeros the Bold"
  And Evelyn opens the lobby of "Lobby 15"
```

`e2e/support/lobby_session.ts` keeps the session id with the title that the feature uses. A step that names another title fails.

To assert a route, write the route shape with placeholders. `fillRouteTemplate` from `e2e/support/guards.ts` puts in the ids from `world`. A placeholder with no stored value fails the step:

```gherkin
Then both Evelyn and Valeros's browsers navigate automatically to "#/campaigns/{campaignId}/sessions/{sessionId}"
```

---

## 3. Write Step Definitions with Shadow-Piercing Locators

Runefoble components are Lit Web Components with Shadow DOM. Playwright locators pierce open shadow roots, so a step does not need custom XPath.

The step `I click the {string} button` finds the button whose accessible name is exactly the feature text. It is defined in `e2e/steps/common_steps.ts`:

```typescript
When('I click the {string} button', async ({ page }, buttonName: string) => {
  const button = page.getByRole('button', { name: buttonName, exact: true });
  await button.click();
});
```

### Selector Rules (Precise Selectors)
- A selector names the element in the feature text. Use `getByRole` with the label and `exact: true`, or scope the locator to the card or row of the named participant.
- Do not add `.first()`, `.nth(0)` or an `.or()` chain to pick "the first match". Playwright strict mode then fails the step when the locator matches zero or several elements.
- If a list can hold several valid matches, `.first()` is allowed only with a comment that says why.
- A control without an accessible name is a component defect. Give the control a label in the component (for example `aria-labelledby`), then select it by that name.
- An assertion must fail when its precondition is missing. Do not wrap a comparison in `if (value)`.

Example from `e2e/steps/character_sheet_steps.ts`. The feature says `checks "Avoid Melee"`:

```typescript
const toggle = guardrails.getByRole('checkbox', { name: toggleLabel, exact: true });
await expect(toggle).toHaveCount(1, { timeout: 10_000 });
await toggle.setChecked(true);
```

### Best Practices for Step Definitions
- **Use Web-First Assertions**: Use `await expect(locator).toBeVisible()` or `expect.poll()`. Playwright then waits for async rendering.
- **Assert Observable Output**: Check the DOM, the URL hash or a public projection. Do not spy on private component methods.
- **Act Through Visible Controls**: A step clicks or types through a control the user sees. Do not set a component field, dispatch a synthetic `CustomEvent`, write `data-theme`, or set `window.location.hash` to skip a flow. A step that cannot find its control must fail. Governed by ADR-0014 and Hard Invariant 7.

Correct pattern, from `e2e/steps/vtt_steps.ts`: launch the session through the DM's button, then drag, then assert the result on the board.

```typescript
const launchBtn = evelynPage
  .locator('runefoble-session-lobby')
  .getByRole('button', { name: 'Launch Session' });
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
- **Prove an Error Path With a Real Refusal**: Do not fake a reply of a Runefoble service with `page.route`. Send a request that the owner service refuses, such as a forge prompt that is too short (`e2e/features/asset_forge.feature`). Assert the status that the page received and the message that the page shows. A fake reply is allowed only for a true external boundary. TASK-0840.
- **Check a Hidden Control Against the Server Flag**: A control that a role does not get must be absent, and the step must prove that the page finished loading. Record the capabilities reply with `openAndRecordCapabilities` (`e2e/support/campaign_capabilities.ts`). Assert the server flag, wait for a sibling element that always renders, then assert `toHaveCount(0)`. Write the positive scenario too, so a control that never renders also fails. See `e2e/steps/session_lobby_roles_steps.ts`.

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

`World` closes every context in `world.extraContexts` after the scenario. The steps in `e2e/steps/vtt_setup_steps.ts` show the pattern for a session lobby. The step `Evelyn creates campaign {string} with session {string} through the gateway` signs Evelyn in on the test page. The step `Valeros and Sarah redeem a player invite to the campaign in separate browsers` opens one context for each player and keeps each player's bearer token for setup calls.

### Personas

Global setup creates the personas in Zitadel before the suite runs. See the [E2E Harness reference](../reference/e2e-harness.md#global-setup-and-personas) for the table. The step name ignores case and punctuation:

| Name in step | Persona key |
|---|---|
| `DM`, `Dungeon Master`, `GM`, `master` | `dm` |
| `Player` | `player` |
| `Evelyn`, `Valeros`, `Sarah`, `Marcus` | The persona with that name |

A name that matches no persona fails the step. Add a new persona to `PERSONA_KEYS` in `e2e/support/personas.ts`. Do not add a fallback.

The step `I am logged in as a {string}` in `e2e/steps/common_steps.ts` accepts any of these names.

---

## 5. Run and Debug

Use these commands from the repository root. The reference page lists what each command runs.

```bash
make test-bdd      # Typecheck, guard unit tests, unused-step check and Gherkin mapping. No browsers.
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
