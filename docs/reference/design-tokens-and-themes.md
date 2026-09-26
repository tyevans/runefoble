# Design Tokens & Themes Reference

This document describes the CSS custom properties, semantic token hierarchy, color palette tokens, and theme system for the Runefoble Lit Web Component frontend.

## Overview & Architecture

Runefoble decouples **visual genre themes** (`data-theme`) from **lighting preferences / color modes** (`data-color-mode`). Both attributes are attached to the root `<html>` element (`document.documentElement`), parameterizing a unified semantic CSS token layer.

Shadow DOM encapsulation in Lit components inherits these tokens transparently, ensuring accessible contrast (WCAG 2.1 AA) and tactile neobrutalist elevation across all permutations without hardcoded hex literals.

```
document.documentElement
 ├── [data-theme="bauhaus | dark-fantasy | parchment | cyber-rune"]
 └── [data-color-mode="light | dark | system"]
```

## Semantic Token Hierarchy

All Web Components consume semantic design tokens rather than raw hex or primitive palette tokens directly.

### 1. Surfaces & Elevation
| Token | Description | Light Default | Dark Default |
|---|---|---|---|
| `--rf-bg-canvas` | Base viewport / body background | `#f8f9fa` | `#121212` |
| `--rf-bg-surface` | Structural panel / container background | `#ffffff` | `#1e1e1e` |
| `--rf-bg-surface-elevated` | Modals, flyouts, tooltips, and floating menus | `#ffffff` | `#252525` |
| `--rf-bg-card` | Tactical cards, feed items, and token panels | `#ffffff` | `#1e1e1e` |
| `--rf-bg-inset` | Recessed areas (input fields, dice tray wells) | `#f1faee` | `#161616` |

### 2. Text & Contrast Hierarchy
| Token | Description | Minimum Contrast |
|---|---|---|
| `--rf-text-primary` | High-emphasis headings, titles, active labels | 7:1 (AAA) |
| `--rf-text-secondary` | Body copy, combatant details, section headers | 4.5:1 (AA) |
| `--rf-text-muted` | Timestamps, placeholder hints, disabled states | 3:1 (AA Large) |
| `--rf-text-inverse` | Text on opposite accent fills | 4.5:1 (AA) |

### 3. Borders & Focus
| Token | Description | Typical Value |
|---|---|---|
| `--rf-border-color` | Primary structural border (ink black or crisp light) | `#121212` / `#f8f9fa` |
| `--rf-border-subtle` | Dividers, grid cell borders, table rows | `rgba(18, 18, 18, 0.15)` |
| `--rf-border-focus` | High-visibility keyboard focus outline | `#e63946` / `#ffb703` |
| `--rf-border-width` | Geometric structural border thickness | `2px` |
| `--rf-border-radius` | Corner radius (Bauhaus 0px, subtle in others) | `0px` |

### 4. Shadows & Tactile Elevation
Hard drop-shadows provide tactile neobrutalist depth. In dark mode, `--rf-shadow-color` dynamically shifts to a translucent luminous or dark edge, preventing invisible black-on-black shadows.
| Token | Formula / Value |
|---|---|
| `--rf-shadow-color` | Dynamic shadow tone (`rgba(18, 18, 18, 1)` or ambient glow) |
| `--rf-shadow` | `4px 4px 0px var(--rf-shadow-color)` |
| `--rf-shadow-sm` | `2px 2px 0px var(--rf-shadow-color)` |

---

## Full Theme Matrix (Theme × Color Mode)

Runefoble defines explicit token sets for both light and dark variations across all 4 themes:

### 1. Bauhaus Modernism (`bauhaus` — Default)
- **Philosophy**: Form follows function, primary colors (cadmium red, cobalt blue, canary yellow), crisp ink borders, and solid offset drop-shadows.
- **Light Mode**:
  - Canvas: `#f8f9fa` | Surface: `#ffffff` | Elevated: `#ffffff`
  - Text: Primary `#121212`, Secondary `#2d3748`, Muted `#4b5563`
  - Borders: `#121212` | Shadow: `4px 4px 0px rgba(18, 18, 18, 1)`
  - Accents: Red `#e63946`, Blue `#1d3557`, Yellow `#ffb703`
- **Dark Mode**:
  - Canvas: `#121212` | Surface: `#1e1e1e` | Elevated: `#252525`
  - Text: Primary `#f8f9fa`, Secondary `#e2e8f0`, Muted `#94a3b8`
  - Borders: `#f8f9fa` | Shadow: `4px 4px 0px rgba(255, 183, 3, 0.5)`
  - Accents: Brightened Red `#f87171`, Sky Blue `#38bdf8`, Amber `#facc15`

### 2. Dark Fantasy (`dark-fantasy`)
- **Philosophy**: Deep slate and obsidian atmosphere with gold and runic violet accents.
- **Dark Mode**:
  - Canvas: `#0f172a` | Surface: `#1e293b` | Inset: `#0b1120`
  - Text: Primary `#f8fafc`, Secondary `#cbd5e1`, Muted `#94a3b8`
  - Borders: `#334155` | Shadow: `4px 4px 0px rgba(0, 0, 0, 0.7)`
  - Accents: Gold `#f59e0b`, Runic Violet `#8b5cf6`, Cyan `#06b6d4`
- **Light Mode**:
  - Canvas: `#f1f5f9` | Surface: `#ffffff` | Inset: `#e2e8f0`
  - Text: Primary `#0f172a`, Secondary `#334155`, Muted `#64748b`
  - Borders: `#475569` | Shadow: `4px 4px 0px rgba(15, 23, 42, 0.6)`
  - Accents: Dark Gold `#d97706`, Royal Violet `#7c3aed`, Deep Cyan `#0891b2`

### 3. Parchment (`parchment`)
- **Philosophy**: Aged paper manuscript aesthetic with antique crimson ink and warm brass accents.
- **Light Mode**:
  - Canvas: `#f4ecd8` | Surface: `#fff9eb` | Inset: `#ebe1c8`
  - Text: Primary `#2e1b0f`, Secondary `#4a301c`, Muted `#6d4c33`
  - Borders: `#5c3a21` | Shadow: `3px 3px 0px rgba(92, 58, 33, 0.8)`
  - Accents: Antique Crimson `#9b2226`, Brass `#bb8524`, Warm Brown `#5c3a21`
- **Dark Mode**:
  - Canvas: `#2b1d14` | Surface: `#3a281c` | Inset: `#21150e`
  - Text: Primary `#f4ecd8`, Secondary `#e2d5bd`, Muted `#a89279`
  - Borders: `#bb8524` | Shadow: `3px 3px 0px rgba(187, 133, 36, 0.4)`
  - Accents: Rose Crimson `#ef4444`, Bright Brass `#fbbf24`, Warm Cream `#f4ecd8`

### 4. Cyber Rune (`cyber-rune`)
- **Philosophy**: Neon dark terminal synthwave with glowing cyan, pink, and yellow.
- **Dark Mode**:
  - Canvas: `#09090b` | Surface: `#18181b` | Inset: `#050507`
  - Text: Primary `#fafafa`, Secondary `#e4e4e7`, Muted `#a1a1aa`
  - Borders: `#27272a` | Shadow: `4px 4px 0px rgba(6, 182, 212, 0.6)`
  - Accents: Neon Cyan `#06b6d4`, Neon Pink `#ec4899`, Neon Yellow `#eab308`
- **Light Mode**:
  - Canvas: `#f0f9ff` | Surface: `#ffffff` | Inset: `#e0f2fe`
  - Text: Primary `#09090b`, Secondary `#1e293b`, Muted `#64748b`
  - Borders: `#0284c7` | Shadow: `4px 4px 0px rgba(2, 132, 199, 0.5)`
  - Accents: Cyan `#0284c7`, Magenta `#db2777`, Amber `#d97706`

---

## Appearance & Color Modes

Color modes allow the user to select between **Light**, **Dark**, and **System** appearance preferences regardless of the chosen aesthetic theme. This is controlled via the `data-color-mode` attribute on `document.documentElement`:

| Mode | `data-color-mode` | Behavior |
|---|---|---|
| Light | `light` | Forces high-contrast light canvas surfaces. |
| Dark | `dark` | Forces dark canvas, surfaces, and inverted structural borders. |
| System | `system` | Reactively mirrors OS preference via `@media (prefers-color-scheme: dark)`. |

Persistence is tracked in `localStorage.getItem('runefoble-color-mode')` (defaulting to `system`).

---

## Web Components

### `<runefoble-settings-modal>`
- **Tag**: `runefoble-settings-modal`
- **Description**: Centralized configuration dialog containing appearance mode toggles (Light / Dark / System), visual theme selection cards with color swatches, audio input preferences, and kinetic dice physics settings.
- **Style Modules** (`frontend/src/components/styles/`):
  - `settings-modal-layout.styles.ts`: Overlay backdrop, dialog container, header, footer actions, and responsive breakpoints.
  - `settings-modal-tabs.styles.ts`: Tab navigation bars, tab panel transitions, radio toggle cards, and setting group titles.
  - `settings-modal-controls.styles.ts`: Swatch chips, selects, checkbox rows, and slider controls.
  - `runefoble-settings-modal.styles.ts`: Composite style export array.
- **Properties**:
  - `open: boolean` (reflected attribute)
  - `currentTheme: 'bauhaus' | 'dark-fantasy' | 'parchment' | 'cyber-rune'`
  - `currentColorMode: 'light' | 'dark' | 'system'`
- **Dispatched CustomEvents**:
  - `color-mode-changed`: `{ detail: { mode: 'light' | 'dark' | 'system', resolvedMode: 'light' | 'dark' } }`
  - `theme-changed`: `{ detail: { theme: string } }`
  - `settings-closed`: `{}`

### `<runefoble-theme-switcher>`
- **Tag**: `runefoble-theme-switcher`
- **Properties**: `currentTheme: 'bauhaus' | 'dark-fantasy' | 'parchment' | 'cyber-rune'`
- **Events**: `theme-changed` with `detail: { theme: string }`
- **Persistence**: Reads and writes `runefoble-theme` in `localStorage`.
