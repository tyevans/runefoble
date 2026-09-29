# How-To: Mount Community Plugin UI Extension Slots

This guide explains how community modders and extension developers can mount custom Lit Web Components into Runefoble's UI extension slots (`hud-widget`, `dice-panel`, and `sidebar-tool`) using the frontend plugin registry, Bauhaus design token inheritance, and Shadow DOM event isolation.

## Overview & Architecture

Runefoble provides extension slots (`<runefoble-plugin-slot>`) to allow third-party tools (such as dice trays, turn timers, mini soundboards, or hex crawlers) to mount into the live VTT interface without altering core frontend code.
- **Shadow DOM Isolation**: Components run within encapsulated DOM boundaries, preventing third-party styles from polluting the App Shell.
- **Design Token Bridge**: Bauhaus CSS custom properties (`--rf-color-*`, `--rf-space-*`, `--rf-font-*`, `--rf-border-*`, etc.) pierce into the slot, ensuring visual harmony with active themes.
- **Dynamic Lifecycle**: The `pluginRegistry` allows registration, unregistration, sorting, and hot-reloading at runtime.

## Step 1: Author a Community Web Component

Create your Lit custom element (or standard Web Component) using Bauhaus theme custom properties:

```typescript
import { LitElement, html, css } from 'lit';
import { customElement, property } from 'lit/decorators.js';

@customElement('community-turn-clock')
export class CommunityTurnClock extends LitElement {
  @property({ type: Number }) secondsRemaining = 60;

  static styles = css`
    :host {
      display: block;
      padding: var(--rf-space-sm, 8px);
      background: var(--rf-bg-surface, #ffffff);
      color: var(--rf-text-primary, #1a202c);
      border: var(--rf-border-width, 2px) solid var(--rf-border-color, #1a202c);
      border-radius: var(--rf-border-radius, 4px);
      font-family: var(--rf-font-family, system-ui, sans-serif);
      font-size: var(--rf-font-size-sm, 0.85rem);
    }
    .accent {
      color: var(--rf-color-accent, #e63946);
      font-weight: 700;
    }
  `;

  render() {
    return html`
      <div>
        <span>Turn Timer:</span>
        <span class="accent">${this.secondsRemaining}s</span>
      </div>
    `;
  }
}
```

## Step 2: Register with Plugin Registry

Register the plugin definition with target slot identifier:

```typescript
import { pluginRegistry } from './components/plugins/plugin_registry.ts';

pluginRegistry.register({
  id: 'mod-turn-clock',
  name: 'Turn Clock',
  slot: 'hud-widget', // or 'dice-panel', 'sidebar-tool'
  tag: 'community-turn-clock',
  author: 'CommunityModder',
  version: '1.0.0',
  order: 10,
  props: { secondsRemaining: 90 },
});
```

### Standard Default Tabletop Plugins

Runefoble seeds default built-in microfrontends into active slots via `registerDefaultPlugins(pluginRegistry, isDm)`:
- **`hud-widget`**: `<runefoble-initiative-tracker>`, `<runefoble-soundscape-controls>`
- **`dice-panel`**: `<runefoble-dice-roller>`, `<runefoble-dice-tray-3d>`
- **`sidebar-tool`**: `<runefoble-combat-reaction-prompt>`, and when authenticated as DM, `<runefoble-dm-whisper-bar>` and `<runefoble-dm-trap-controls>`

## Step 3: Embed an Extension Slot in Layouts

Place `<runefoble-plugin-slot>` at the desired extension point in the markup:

```html
<!-- Mounted in HUD, Sidebar, or Dice Tray -->
<runefoble-plugin-slot slot-id="hud-widget" orientation="horizontal"></runefoble-plugin-slot>
<runefoble-plugin-slot slot-id="sidebar-tool" orientation="vertical"></runefoble-plugin-slot>
<runefoble-plugin-slot slot-id="dice-panel" .showFallback=${false}></runefoble-plugin-slot>
```

When no plugins are registered, the slot displays an accessible fallback placeholder unless `.showFallback=${false}` is set.

## Step 4: Dispatch Sandboxed Events

When emitting custom events from your plugin, use `createSandboxedEvent` to retain plugin origin metadata and maintain Shadow DOM encapsulation:

```typescript
import { createSandboxedEvent } from './components/plugins/plugin_sandbox.ts';

const event = createSandboxedEvent(
  myPluginDef,
  'timer-expired',
  { expiredAt: Date.now() },
  { bubbles: true, composed: false }
);
this.dispatchEvent(event);
```

## Step 5: Verify in Storybook

Interactive visual verification stories live in `frontend/src/stories/runefoble-plugin-slot.stories.ts`. Run the Storybook development server to verify Light and Dark mode contrast:

```bash
pnpm --prefix frontend storybook
```
