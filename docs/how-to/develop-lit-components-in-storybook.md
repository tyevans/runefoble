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
