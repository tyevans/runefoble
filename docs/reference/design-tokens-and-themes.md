# Design Tokens & Themes Reference

This document describes the CSS custom properties, color palette tokens, and theme system for the Runefoble Lit Web Component frontend.

## Themes

Themes are controlled by setting the `data-theme` attribute on the root `<html>` element (`document.documentElement`).

Supported theme identifiers:
- `bauhaus` (Default)
- `dark-fantasy`
- `parchment`
- `cyber-rune`

## Token Definitions

### Bauhaus Modernism (`bauhaus` — Default)
- **Philosophy**: Form follows function, geometric clarity, bold primary blocks, crisp ink borders, and solid offset drop-shadows.
- **Palette**:
  - `--rf-color-red`: `#e63946` (Cadmium Red)
  - `--rf-color-blue`: `#1d3557` (Cobalt Blue)
  - `--rf-color-yellow`: `#ffb703` (Canary Yellow)
  - `--rf-color-dark`: `#121212` (Ink Black)
  - `--rf-color-light`: `#ffffff` (White)
  - `--rf-bg-canvas`: `#f8f9fa` (Off-white Canvas)
  - `--rf-bg-surface`: `#ffffff` (Surface)
  - `--rf-bg-card`: `#ffffff` (Card Surface)
  - `--rf-border-color`: `#121212`
  - `--rf-border-width`: `2px`
  - `--rf-border-radius`: `0px`
  - `--rf-shadow`: `4px 4px 0px #121212`
  - `--rf-shadow-sm`: `2px 2px 0px #121212`
  - `--rf-text-primary`: `#121212`
  - `--rf-text-muted`: `#4b5563`
  - `--rf-accent-primary`: `var(--rf-color-red)`
  - `--rf-accent-secondary`: `var(--rf-color-blue)`
  - `--rf-accent-tertiary`: `var(--rf-color-yellow)`

### Dark Fantasy (`dark-fantasy`)
- **Philosophy**: Deep slate and obsidian atmosphere with gold and runic violet accents.
- **Tokens**:
  - Canvas: `#0f172a`
  - Surface / Card: `#1e293b`
  - Border: `#334155` (1px, 8px radius)
  - Accents: Gold (`#f59e0b`) & Runic Purple (`#8b5cf6`)
  - Shadow: `0 4px 12px rgba(0, 0, 0, 0.5)`

### Parchment (`parchment`)
- **Philosophy**: Aged paper manuscript aesthetic with antique crimson ink and warm brass accents.
- **Tokens**:
  - Canvas: `#f4ecd8`
  - Surface / Card: `#fff9eb`
  - Border: `#5c3a21` (2px, 4px radius)
  - Accents: Antique Crimson (`#9b2226`) & Brass (`#bb8524`)
  - Shadow: `3px 3px 0px #5c3a21`

### Cyber Rune (`cyber-rune`)
- **Philosophy**: Neon dark synthwave terminal with high-contrast glowing cyan and pink highlights.
- **Tokens**:
  - Canvas: `#09090b`
  - Surface / Card: `#18181b`
  - Border: `#27272a` (1px, 2px radius)
  - Accents: Neon Cyan (`#06b6d4`), Neon Pink (`#ec4899`), Neon Yellow (`#eab308`)
  - Shadow: `0 0 10px rgba(6, 182, 212, 0.3)`

## Appearance & Color Modes

Color modes allow the user to select between **Light**, **Dark**, and **System** appearance preferences regardless of the chosen aesthetic theme. This is controlled via the `data-color-mode` attribute on `document.documentElement`:

| Mode | `data-color-mode` | Behavior |
|---|---|---|
| Light | `light` | Forces high-contrast light canvas surfaces. |
| Dark | `dark` | Forces dark canvas, surfaces, and inverted structural borders. |
| System | `system` | Reactively mirrors OS preference via `@media (prefers-color-scheme: dark)`. |

Persistence is tracked in `localStorage.getItem('runefoble-color-mode')` (defaulting to `system`).

## Web Components

### `<runefoble-settings-modal>`
- **Tag**: `runefoble-settings-modal`
- **Description**: Centralized Bauhaus modernist configuration dialog containing appearance mode toggles, visual theme selection cards with color swatches, audio input preferences, and kinetic dice physics settings.
- **Properties**:
  - `open: boolean` (reflected attribute)
  - `currentTheme: 'bauhaus' | 'dark-fantasy' | 'parchment' | 'cyber-rune'`
  - `currentColorMode: 'light' | 'dark' | 'system'`
- **Dispatched CustomEvents**:
  - `color-mode-changed`: `{ detail: { mode: 'light' | 'dark' | 'system', resolvedMode: 'light' | 'dark' } }`
  - `theme-changed`: `{ detail: { theme: string } }`
  - `settings-closed`: `{}`
- **Accessibility & Focus**:
  - Encapsulated backdrop overlay (`backdrop-filter: blur(4px)`).
  - ARIA attributes: `role="dialog"`, `aria-modal="true"`, `aria-labelledby="settings-modal-title"`.
  - Dismissible via backdrop click, `Escape` key, or close button. Focus is trapped while open and restored to trigger on close.

### `<runefoble-theme-switcher>`
- **Tag**: `runefoble-theme-switcher`
- **Properties**: `currentTheme: 'bauhaus' | 'dark-fantasy' | 'parchment' | 'cyber-rune'`
- **Events**: `theme-changed` with `detail: { theme: string }`
- **Persistence**: Reads and writes `runefoble-theme` in `localStorage`.

