# How-To: Authoring Service Microfrontends

This guide walks through creating or extending a frontend microfrontend component within a service bounded context (`services/<bc>/ui/`).

## Step 1: Create the Component in the Service Bounded Context

Create your Lit custom element in `services/<service_name>/ui/src/<component-name>.ts`:

```typescript
import { LitElement, html, css } from 'lit';
import { customElement, property } from 'lit/decorators.js';

@customElement('runefoble-my-feature')
export class RunefobleMyFeature extends LitElement {
  @property({ type: String }) title = 'Feature';

  static styles = css`
    :host {
      display: block;
      font-family: var(--rf-font-family, system-ui, sans-serif);
      color: var(--rf-text-primary, #121212);
      background: var(--rf-bg-surface, #ffffff);
      border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
      box-shadow: var(--rf-shadow, 4px 4px 0px #121212);
      padding: 16px;
    }
  `;

  render() {
    return html`<div><h3>${this.title}</h3></div>`;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'runefoble-my-feature': RunefobleMyFeature;
  }
}
```

## Step 2: Export Component from the Package Index

Add the component to `services/<service_name>/ui/src/index.ts`:

```typescript
export * from './runefoble-my-feature.ts';
```

## Step 3: Add an Interactive Story in the Service UI

Create `services/<service_name>/ui/src/<component-name>.stories.ts` following Hard Invariant 3:

```typescript
import type { Meta, StoryObj } from '@storybook/web-components';
import { html } from 'lit';
import './runefoble-my-feature.ts';

const meta: Meta = {
  title: 'Feature/RunefobleMyFeature',
  component: 'runefoble-my-feature',
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj;

export const Default: Story = {
  render: () => html`<runefoble-my-feature title="Sample Feature"></runefoble-my-feature>`,
};
```

## Step 4: Register in Service Frontdoor Manifest

In `services/<service_name>/src/<service_name>/main.py`, include the custom element in the `/ui/manifest` endpoint:

```python
@app.get("/ui/manifest")
def get_ui_manifest():
    return {
        "service": "<service_name>",
        "package": "@runefoble/<service_name>-ui",
        "components": ["runefoble-my-feature"],
        "version": "0.1.0",
    }
```

## Step 5: Verify in Storybook & Build

Run the developer Storybook target to inspect your component in isolation:

```bash
make dev-storybook
```

Verify that the TypeScript build and test suite pass cleanly:

```bash
make test
make lint
```
