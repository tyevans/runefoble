# How-To: Develop Lit Components in Storybook

## Overview
All frontend widgets (tactical boards, cards, feeds, dice trays) are built first in Storybook using Lit Web Components.

## Workflow

### 1. Launch Storybook
```bash
make dev-storybook
```
Storybook will open at `http://localhost:6006`.

### 2. Create the Lit Element in the Service Bounded Context
Put each element in the owning service UI package, `services/<bc>/ui/src/`. Do not put components in `frontend/`. Hard Invariant 3 requires this.

Export the element from `services/<bc>/ui/src/index.ts`.

For the full flow, follow [Authoring Service Microfrontends](authoring-service-microfrontends.md).

### 3. Create the Story Beside the Element
Put the story in the same folder as the element, for example `services/<bc>/ui/src/<component-name>.stories.ts`. Storybook loads every `services/*/ui/src/**/*.stories.ts` file.

The story imports the element from the same folder. The authoring guide shows a complete example.

### 4. Verify the Story in Storybook
Open the story in Storybook at `http://localhost:6006`. Check the browser console. A story must show zero console errors.

### 5. Type-Check Stories
Stories are part of the component contract. Storybook builds with esbuild and does not type-check, so each UI package type-checks its stories through its own `tsconfig.json`. The `src` directory is in `include` and no story file is excluded.

Run the check for one package:
```bash
pnpm --filter ./services/<bc>/ui run typecheck
```
A story with a wrong prop type or a missing component import fails this check. Fix the story to match the component API. Do not change the component API only to satisfy a story.

### 6. Reference Portrait Images in Stories
Storybook does not serve a static asset directory. A story that requests a path such as `/assets/portraits/fighter.svg` logs a 404 error and fails the zero-console-error rule.

Use the shared Bauhaus portrait placeholders from `@runefoble/ui-core` instead:
```typescript
import { PORTRAIT_PLACEHOLDERS } from '@runefoble/ui-core';

const hero = { name: 'Valeros', portraitUrl: PORTRAIT_PLACEHOLDERS.fighter };
```
The available ids are `fighter`, `wizard`, `cleric`, `rogue` and `paladin`. Each value is an inline SVG data URI. Add a new id in `libs/runefoble_ui/src/portrait-placeholders.ts` when a story needs another class.

The `pnpm run lint` step in `frontend/` runs `frontend/scripts/check-asset-paths.ts`. It fails when any source file under `frontend/`, `services/`, `libs/` or `gateway/` names an `/assets/` path that no package serves from its `public/` directory. Use a placeholder, or add the file to a package `public/` directory.

### 7. Unit-Test a Lit Element in a Browser
Node cannot load Lit decorators or a DOM. Test an element in headless Chromium instead.

The harness is Vitest browser mode with the Playwright provider. Chromium comes from the Playwright install that the E2E suite already uses. jsdom is not used, because it does not give real custom elements, Shadow DOM or blob URLs.

The shared configuration is `vitest.dom.config.ts` at the repository root. A package that has element tests keeps a one-line `vitest.config.ts`:
```typescript
import { domTestConfig } from '../../../vitest.dom.config.ts';

export default domTestConfig(import.meta.dirname);
```
Adjust the relative path to reach the repository root. Put element tests in `test-dom/*.test.ts` in the package. Node unit tests stay in `test/`. The package `test` script runs both:
```json
"test": "node --experimental-strip-types --test test/*.test.ts && vitest run"
```
Import the element in the test, then assert on the rendered DOM:
```typescript
import '../src/runefoble-character-card.ts';
```

Rules for element tests:
- Fake only the network. Stub `fetch` with `vi.stubGlobal('fetch', ...)`. Do not stub the code under test.
- To test a transport call, use a live loopback upstream instead of a stub. Pass `loopbackUpstreamCommands` from `libs/runefoble_ui/testing/loopback-commands.ts` as `domTestConfig(import.meta.dirname, { commands: loopbackUpstreamCommands })`. In the test, read `commands` from `vitest/browser`. Set the element `apiBaseUrl` to `await commands.upstreamUrl()`. Set the reply with `upstreamReply(status, body)`. Read what arrived with `upstreamRequests()`. See [UI transport](../reference/ui-transport.md).
- Assert what a user sees: `src` attributes, text, and which elements exist.
- Check blob URL cleanup with the browser. Fetch the old `blob:` URL and expect it to reject after revocation.
- Prove the test can fail. Remove the behaviour for a moment and confirm the test turns red.

Run one package:
```bash
pnpm --filter @runefoble/ui-core test
```
The packages with element tests have a `vitest.config.ts`. They are `libs/runefoble_ui`, `frontend/` and the UI packages of `asset_forge`, `board_state`, `campaign_lore`, `character_sheet`, `game_session` and `rules_compendium`.

### 8. Bind Attributes and SVG Fragments Correctly
Two Lit mistakes give no error. The element only shows wrong data, or nothing.

**Kebab-case attributes.** Without `attribute:`, Lit observes the lower-case property name. A property `campaignId` observes `campaignid`, not `campaign-id`. When a parent sets `campaign-id="..."`, the property keeps its default value.

Name the attribute when a template, a story or a test sets the kebab-case form:
```typescript
@property({ type: String, attribute: 'campaign-id' }) campaignId = '';
```
To pass a value with no attribute, bind the property: `.campaignId=${id}`.

**SVG fragments.** Lit parses an `html` template in the HTML namespace. A `<g>`, `<circle>`, `<polygon>` or `<text>` in an `html` template is an HTML element. It has no geometry and does not show. Write each fragment that goes inside an `<svg>` with the `svg` tag:
```typescript
import { svg, type SVGTemplateResult } from 'lit';

export const renderPin = (pin: AtlasPin): SVGTemplateResult =>
  svg`<g class="pin"><text class="pin-label">${pin.title}</text></g>`;
```
The `<svg>` element itself can stay in the `html` template.

**The check.** `make lint` runs `scripts/check_lit_templates.py`. Run it alone:
```bash
uv run python scripts/check_lit_templates.py
```
The check reads the `@property` declarations of each Runefoble element in `frontend/src`, `services/*/ui/src` and `libs/*/src`. It fails on these cases:
- A template or HTML string sets a kebab-case attribute on the element, and the matching camelCase property does not observe that attribute.
- A `setAttribute('kebab-name', ...)` call in a file that names the element sets such an attribute.
- An `html` template starts with an SVG-only element such as `<g>`, `<circle>` or `<text>`.

The check also reads `test/` and `test-dom/` in each UI package. It skips `data-*` and `aria-*` attributes, and attributes that match no property. It cannot see a template that starts with an interpolation before the first SVG element. In a DOM test, assert `namespaceURI` and `getBBox()` of the SVG element (see `services/campaign_lore/ui/test-dom/atlas-svg-layers.test.ts`).

