# How-To: Develop Lit Components in Storybook

## Overview
All frontend widgets (tactical boards, cards, feeds, dice trays) are built first in Storybook using Lit Web Components.

## Workflow

### 1. Launch Storybook
```bash
make dev-storybook
```
Storybook will open at `http://localhost:6006`.

### 2. Create the Lit Element
In `frontend/src/components/<component-name>.ts`:
```typescript
import { LitElement, html, css } from 'lit';
import { customElement, property } from 'lit/decorators.js';

@customElement('runefoble-dice-tray')
export class RunefobleDiceTray extends LitElement {
  static styles = css`
    :host { display: block; padding: 12px; background: #1e293b; border-radius: 8px; }
  `;

  @property({ type: Number }) result = 20;

  render() {
    return html`<div>Die Result: ${this.result}</div>`;
  }
}
```

### 3. Create the Story
In `frontend/src/stories/<component-name>.stories.ts`:
```typescript
import type { Meta, StoryObj } from '@storybook/web-components';
import { html } from 'lit';
import '../components/runefoble-dice-tray.ts';

const meta: Meta = {
  title: 'TTRPG/RunefobleDiceTray',
  component: 'runefoble-dice-tray',
};

export default meta;
type Story = StoryObj;

export const CriticalHit: Story = {
  render: () => html`<runefoble-dice-tray .result=${20}></runefoble-dice-tray>`,
};
```

### 4. Build and Verify
Run:
```bash
make test
```
This builds TypeScript and verifies the static Storybook bundle without errors.

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
