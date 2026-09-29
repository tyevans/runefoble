# ADR-0014: Behavior-Driven Development (BDD) with Gherkin User Stories and Playwright End-to-End Validation

## Status
Accepted

## Context
Runefoble is a collaborative tabletop roleplaying platform composed of decoupled Lit Web Component microfrontends, real-time WebSockets, streaming audio, and event-sourced Python microservices governed by SpiceDB Zanzibar authorization.

While the monorepo enforces unit testing, isolated Storybook component verification (ADR-0004, ADR-0013), and backend blackbox testing via pytest, critical end-to-end user journeys spanning multiple microfrontends and live services lacked unified verification:
1. **Disconnected Verification Layers**: Frontend components were verified in Storybook isolation using static mock props, while backend services were tested with Python HTTP clients. Real browser execution—such as SPA hash routing, DOM event bubbling, Shadow DOM piercing, real WebSocket connections, and cookie/JWT authorization—was not tested end-to-end.
2. **Untested Gherkin Scenarios**: Product requirements and user stories (`docs/project/user_stories/accepted/`) were already structured with Gherkin scenarios (`Given ... When ... Then ...`), but existed purely as markdown documentation without an automated test runner.
3. **Risk of Backdoor State Manipulation and Mock Masking**: Without automated end-to-end browser tests, integration regressions (such as dead-end tabs with `e.preventDefault()`, unhandled custom events on custom elements, and static fallback arrays masking 502 proxy errors) escaped detection.

## Decision
We adopt **Behavior-Driven Development (BDD)** driven by **Gherkin User Stories** and automated through **Playwright** (`@playwright/test`):

1. **Gherkin as the Single Source of Truth for User Flows**:
   - User stories in `docs/project/user_stories/accepted/` must articulate end-to-end value from the persona perspective using standard Gherkin syntax (`Feature`, `Scenario`, `Given`, `When`, `Then`, `And`).
   - Feature files are maintained under `e2e/features/` (or mirrored from user stories), ensuring scenarios remain executable specifications.

2. **Playwright as the Browser Automation Engine**:
   - We utilize Playwright with a BDD runner (`playwright-bdd` / TypeScript step definitions) to execute Gherkin scenarios across modern browsers (Chromium, Firefox, WebKit).
   - Playwright's native shadow-piercing locators (`page.locator('runefoble-board >> canvas')` or `getByRole`) are used to interact with Lit Web Components across Shadow DOM boundaries without breaking encapsulation.

3. **Strict Blackbox Frontdoor Testing Invariant**:
   - Consistent with Hard Invariant 7, **zero private backdoors or direct database manipulations are permitted in BDD step definitions**.
   - **Setup (`Given`)**: State is prepared exclusively through public frontdoors: public HTTP REST APIs (`POST /api/v1/campaigns`, `POST /api/v1/characters`), Zitadel OIDC authentication, or browser localStorage token injection.
   - **Actions (`When`)**: Executed via realistic browser interactions: clicking buttons, entering text, selecting dropdown options, dragging board tokens, and triggering hotkeys.
   - **Verification (`Then`)**: Assertions must observe public, user-visible outcomes: rendered DOM elements, active navigation routes, toast notifications, visual feedback, live WebSocket state reflections, or published CloudEvents.

4. **Definition of Ready (DoR) Governance Evolution**:
   - Before any user-facing task or feature can move from `proposed/` to `refined/`, its governing user story must provide executable Gherkin scenarios with frontdoor-only setup.

5. **Definition of Done (DoD) Governance Evolution**:
   - A user-facing feature cannot move from `refined/` to `complete/` until its Gherkin scenarios are implemented as passing Playwright BDD tests executed against live running services.

6. **Tooling & CI Integration**:
   - The root `Makefile` provides targets: `test-e2e` (headless Playwright BDD run), `test-e2e-ui` (interactive Playwright UI mode), and `test-bdd`.
   - Playwright BDD execution is integrated into the GitHub Actions CI pipeline (`.github/workflows/ci.yml`) as a blocking merge gate for user-facing changes.

## Consequences

- **Positive**:
  - **Living Executable Specifications**: User stories serve as active test suites rather than passive documentation.
  - **True End-to-End Validation**: Validates SPA client routing, Lit Shadow DOM events, WebSocket synchronization, and backend services simultaneously.
  - **Eliminates Mock Blindspots**: Exposes dead interface elements, broken proxy configurations, and unhandled custom events early.
  - **Cross-Browser Verification**: Guarantees consistent player and DM experiences across Chromium, Firefox, and WebKit.
- **Negative**:
  - Requires local services or test containers (API Gateway, Redis, SpiceDB) running during end-to-end test execution.
  - Browser test execution takes longer than unit tests; managed via parallel workers, targeted smoke suites, and CI caching.
