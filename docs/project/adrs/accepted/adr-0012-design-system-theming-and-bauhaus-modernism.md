# ADR-0012: Design System Theming Tokens and Bauhaus Modernist Aesthetic

## Status
Accepted

## Context
Runefoble's user interface is constructed using Lit Web Components and Vite (governed by ADR-0004). Tabletop roleplaying tools often default to generic muddy brown parchment or uninspired flat dark interfaces.

To make Runefoble visually distinctive, tactile, and instantly readable during live tabletop play and voice streaming, we adopt **Bauhaus Modernism** as the foundational design system and default theme:
- Form follows function: zero visual clutter, high information density, stark visual hierarchy.
- Geometry: pure circles, squares, grids, and crisp linear divisions.
- Primary color theory: cadmium red, cobalt blue, warm canary yellow, grounded by ink black and off-white canvas.
- Structural borders and offset hard drop-shadows (neobrutalist geometric tactile feel).

At the same time, tabletop gaming encompasses many genres (cyberpunk, gothic horror, high fantasy). Therefore, the frontend must support dynamic runtime themability.

## Decision
1. **Design Tokens via CSS Custom Properties**:
   Establish standard `--rf-theme-*` CSS custom properties on `:root` and `[data-theme="..."]`:
   - Colors: `--rf-accent-red`, `--rf-accent-blue`, `--rf-accent-yellow`, `--rf-bg-canvas`, `--rf-bg-surface`, `--rf-border-color`, `--rf-text-primary`, `--rf-text-muted`.
   - Geometry: `--rf-border-width`, `--rf-border-radius`, `--rf-shadow-offset`, `--rf-font-family`.
2. **Default Theme is Bauhaus**:
   When no user preference is stored, the active theme defaults to `bauhaus`:
   - Canvas: `#f8f9fa` (clean high-contrast off-white) or `#f4f1de`
   - Primary: `#d62828` / `#e63946`
   - Secondary: `#1d3557` / `#00509d`
   - Accent: `#f7b731` / `#fcbf49`
   - Ink: `#121212`
   - Borders: `2px solid #121212`
   - Shadow: `4px 4px 0px #121212`
3. **Multi-Theme Support**:
   Provide built-in palettes:
   - `bauhaus` (Default)
   - `dark-fantasy` (Obsidian, runic violet, gold)
   - `parchment` (Aged paper, warm sepia, dark ink)
   - `cyber-rune` (Synthwave neon cyan, magenta, dark grid)
4. **Theme Persistence and Switcher**:
   A dedicated `<runefoble-theme-switcher>` component syncs theme state with `localStorage.getItem('runefoble-theme')` and sets `document.documentElement.dataset.theme`.
5. **Component Encapsulation**:
   Web Components consume design tokens through CSS variables in their `static styles = css` blocks, ensuring Shadow DOM encapsulation while inheriting root theme variables.

## Consequences
- **Positive**:
  - Distinctive visual identity that makes board states and character stats instantly legible.
  - Zero performance cost for theme switching (pure CSS variable cascades, no re-rendering of DOM trees).
  - Streamers and GMs can easily match the UI mood to their current campaign setting.
- **Negative**:
  - Shadow DOM components must consistently reference `var(--rf-*)` instead of hardcoded hex colors.
