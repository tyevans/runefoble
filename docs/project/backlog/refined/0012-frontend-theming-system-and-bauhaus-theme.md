---
id: 0012
title: Frontend Theming System with Bauhaus Modernist Default
status: Refined
created: 2026-09-25
dependencies: [TASK-0004, TASK-0010]
governing_adrs: [ADR-0004, ADR-0012]
target_release: 0.1.0
---

# TASK-0012 — Frontend Theming System with Bauhaus Modernist Default

## Summary
Implement a design token theming architecture across the Runefoble Lit Web Component frontend (US-0016, ADR-0012). The default theme is **Bauhaus Modernism**, characterized by bold primary color blocks (cadmium red, cobalt blue, yellow), deep ink black borders (`2px solid #121212`), high-contrast off-white canvas, clean geometric sans typography, and offset solid drop-shadows (`4px 4px 0px #121212`). Provide support for alternate themes (`dark-fantasy`, `parchment`, `cyber-rune`), an interactive `<runefoble-theme-switcher>` component, local storage persistence, and Storybook stories demonstrating theme variations.

## Scope & Changes
1. **Design Tokens & Theme Styles (`frontend/src/styles/themes.css`)**:
   - Define root CSS variables:
     - `bauhaus` (Default):
       - `--rf-bg-canvas`: `#f8f9fa`
       - `--rf-bg-surface`: `#ffffff`
       - `--rf-bg-elevated`: `#ffffff`
       - `--rf-text-primary`: `#121212`
       - `--rf-text-muted`: `#4b5563`
       - `--rf-border-color`: `#121212`
       - `--rf-border-width`: `2px`
       - `--rf-border-style`: `solid`
       - `--rf-border-radius`: `0px`
       - `--rf-shadow-offset`: `4px 4px 0px #121212`
       - `--rf-color-red`: `#d62828`
       - `--rf-color-blue`: `#1d3557`
       - `--rf-color-yellow`: `#f7b731`
       - `--rf-color-dark`: `#121212`
       - `--rf-color-light`: `#f8f9fa`
     - `dark-fantasy`:
       - Deep slate/obsidian canvas (`#0f172a`), runic purple/gold borders, soft glow shadows.
     - `parchment`:
       - Warm aged parchment canvas (`#f4ecd8`), dark sepia ink, classic rounded borders.
     - `cyber-rune`:
       - Cyberpunk obsidian canvas (`#0d0221`), neon cyan (`#00f5d4`), magenta (`#f72585`).
2. **Theme Switcher Component (`frontend/src/components/runefoble-theme-switcher.ts`)**:
   - `<runefoble-theme-switcher>` custom Lit component.
   - Shows active theme badge and dropdown/toggle buttons for `bauhaus`, `dark-fantasy`, `parchment`, `cyber-rune`.
   - Reads/writes `localStorage.getItem('runefoble-theme')` and sets `document.documentElement.dataset.theme`.
   - Dispatch `theme-changed` custom event.
3. **Component Theme Variable Adoption**:
   - Update `frontend/src/components/runefoble-board.ts`, `frontend/src/components/runefoble-character-card.ts`, `frontend/src/components/runefoble-watcher-feed.ts`, and `frontend/src/runefoble-app.ts` to consume `--rf-*` theme tokens.
4. **Storybook Stories (`frontend/src/stories/theme-switcher.stories.ts`)**:
   - Interactive stories demonstrating theme switching and previewing Bauhaus elements.
5. **Testing**:
   - TypeScript build check (`pnpm run build`).
   - Storybook build check.
   - File length limit (<500 lines) verified.
