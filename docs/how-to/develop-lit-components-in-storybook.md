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
- Assert what a user sees: `src` attributes, text, and which elements exist.
- Check blob URL cleanup with the browser. Fetch the old `blob:` URL and expect it to reject after revocation.
- Prove the test can fail. Remove the behaviour for a moment and confirm the test turns red.

Run one package:
```bash
pnpm --filter @runefoble/ui-core test
```
The packages with element tests are `libs/runefoble_ui` (`@runefoble/ui-core`), `services/character_sheet/ui` (`@runefoble/character-sheet-ui`) and `frontend/`.
