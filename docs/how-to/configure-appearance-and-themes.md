# How to Configure Appearance, Color Modes, and Themes

This practical guide demonstrates how to configure global visual themes and appearance modes (Dark, Light, System) in the Runefoble application, trigger the `<runefoble-settings-modal>` dialog, and react to theming events in Lit Web Components.

## Prerequisites

- Frontend workspace initialized (`pnpm install`).
- Basic familiarity with CSS Custom Properties and Lit Web Components.

## 1. Opening the Settings Modal

The application header provides a compact, Bauhaus-styled settings trigger button (`#settings-trigger-btn`):

```html
<button
  id="settings-trigger-btn"
  class="settings-trigger"
  aria-haspopup="dialog"
  aria-expanded="false"
  aria-label="Open settings"
>
  <span class="settings-icon" aria-hidden="true">⚙️</span>
  <span class="settings-label">Settings</span>
</button>
```

When clicked, the button toggles the `open` property on `<runefoble-settings-modal>`:

```typescript
private openSettings() {
  this.isSettingsOpen = true;
}
```

## 2. Choosing Color Modes (Light / Dark / System)

Within the modal's **Appearance & Theme** tab, users can select between three color modes:

1. ☀️ **Light Mode**: Sets `data-color-mode="light"` on `document.documentElement`.
2. 🌙 **Dark Mode**: Sets `data-color-mode="dark"` on `document.documentElement`, shifting canvas and surface backgrounds to charcoal tones (`#121212`) and inverting structural borders.
3. 💻 **System Mode** (Default): Sets `data-color-mode="system"` and automatically responds to OS preferences via `window.matchMedia('(prefers-color-scheme: dark)')`.

Choices are automatically persisted in `localStorage.getItem('runefoble-color-mode')`.

## 3. Switching Visual Themes

Users can select from four tactile genre themes by clicking their respective cards:

- **Bauhaus Modernist** (`bauhaus`): Bold primary geometric blocks (Cadmium Red, Cobalt Blue, Canary Yellow), solid drop-shadows (`4px 4px 0px #121212`), and clean sans typography.
- **Dark Fantasy** (`dark-fantasy`): Obsidian surfaces (`#0f172a`), runic purple, and radiant gold accents.
- **Parchment** (`parchment`): Aged manuscript canvas (`#f4ecd8`), antique crimson, and brass borders.
- **Cyber Rune** (`cyber-rune`): High-contrast dark synthwave terminal with neon cyan (`#06b6d4`) and pink (`#ec4899`).

The active theme is assigned to `document.documentElement.setAttribute('data-theme', theme)` and saved under `localStorage.getItem('runefoble-theme')`.

## 4. Subscribing to Theming Events

Components can listen to custom events dispatched by `<runefoble-settings-modal>`:

```typescript
// Subscribing to color mode updates
modal.addEventListener('color-mode-changed', (event: CustomEvent) => {
  const { mode, resolvedMode } = event.detail;
  console.log(`Active mode: ${mode}, Resolved appearance: ${resolvedMode}`);
});

// Subscribing to theme changes
modal.addEventListener('theme-changed', (event: CustomEvent) => {
  const { theme } = event.detail;
  console.log(`Active theme: ${theme}`);
});

// Subscribing to modal closure
modal.addEventListener('settings-closed', () => {
  console.log('Settings dialog closed; focus restored to trigger');
});
```

## 5. Testing Themes in Storybook

To visually inspect all modal states and theme permutations:

```bash
make dev-storybook
```

Navigate to **Settings** → **RunefobleSettingsModal** in the Storybook sidebar to test:
- `DefaultClosedTrigger`
- `OpenLightMode`
- `OpenDarkMode`
- `OpenSystemMode`
- `ActiveThemeCyberRune`, `ActiveThemeDarkFantasy`, `ActiveThemeParchment`
