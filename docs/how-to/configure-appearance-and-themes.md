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

Users can select from four tactile genre themes by clicking their respective cards. With the decoupled color mode architecture, each theme supports both Light and Dark mode variations via semantic tokens:

- **Bauhaus Modernist** (`bauhaus`): Bold primary geometric blocks (Cadmium Red, Cobalt Blue, Canary Yellow), crisp structural borders, and tactile drop-shadows (`4px 4px 0px var(--rf-shadow-color)`).
- **Dark Fantasy** (`dark-fantasy`): Obsidian slate surfaces (`#0f172a` in dark mode) or illuminated cathedral parchment (`#f1f5f9` in light mode), runic purple, and radiant gold accents.
- **Parchment** (`parchment`): Aged manuscript canvas (`#f4ecd8` in light mode, `#2b1d14` in dark mode), antique crimson, and brass borders.
- **Cyber Rune** (`cyber-rune`): High-contrast synthwave terminal (`#09090b` in dark mode) or high-tech blueprint (`#f0f9ff` in light mode) with neon cyan and pink accents.

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

## 5. Modular Tab Panels and Sub-Controllers

The settings dialog uses a modular architecture decomposed into dedicated subcomponents:
- `<runefoble-settings-appearance>`: Theme cards, color mode radio chips, and palette swatches.
- `<runefoble-settings-audio>`: Microphone device dropdown, adaptive noise suppression, and status indicators.
- `<runefoble-settings-dice>`: 3D kinetic dice physics toggles, spatial foley audio switches, and d20 test roll buttons.
- `ThemeSettingsController`: Lit ReactiveController managing `localStorage` synchronization and OS media query tracking.

### Modular Style Architecture

In accordance with Hard Invariant 6 (File length limit < 500 lines), modal styles are decomposed into single-responsibility Lit CSS sub-modules in `frontend/src/components/styles/`:
- `settings-modal-layout.styles.ts`: Backdrop overlay, dialog container animations, header, responsive breakpoints, and footer action buttons.
- `settings-modal-tabs.styles.ts`: Tab navigation bar, panel transitions, radio toggle cards, and setting group titles.
- `settings-modal-controls.styles.ts`: Palette swatches, select menus, range sliders, and checkbox toggles.
- `runefoble-settings-modal.styles.ts`: Clean composite export aggregating `[layoutStyles, tabsStyles, controlsStyles]`.

## 6. Testing Themes and Tab Panels in Storybook

To visually inspect modal states and individual tab panels:

```bash
make dev-storybook
```

Navigate to **Settings** → **RunefobleSettingsModal** or **Settings** → **TabPanels** to inspect `DefaultClosedTrigger`, `OpenLightMode`, `OpenDarkMode`, `OpenSystemMode`, `AppearanceTabPanel`, `AudioTabPanel`, and `DiceTabPanel`.
