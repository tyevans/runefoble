---
id: '0074'
title: Design System Dark and Light Mode Color Tokens & Cross-Component Contrast Invariants
status: Refined
created: 2026-09-25
dependencies:
- TASK-0012
- TASK-0073
governing_adrs:
- ADR-0004
- ADR-0012
target_release: 0.1.0
---
# TASK-0074 — Design System Dark and Light Mode Color Tokens & Cross-Component Contrast Invariants

## Summary
Audit, standardize, and implement comprehensive Dark Mode and Light Mode design tokens across `frontend/src/styles/themes.css` and all Runefoble Lit Web Components. Decouple color mode (`data-color-mode="light | dark"`) from genre themes (`data-theme="bauhaus | dark-fantasy | parchment | cyber-rune"`), ensuring every component and theme renders with proper semantic surfaces, accessible contrast (WCAG 2.1 AA), and tactile border/shadow aesthetics regardless of active lighting preference.

## Problem Statement & Context
Following initial theming in TASK-0012, themes were created as monolithic color sets (e.g. Bauhaus was fixed as a light canvas `#f8f9fa`, Dark Fantasy as dark `#0f172a`). This created several UX and accessibility defects:
1. **No True Mode Toggle**: A user wanting Bauhaus geometric minimalism in a dark room had no way to toggle dark mode.
2. **Hardcoded Component Colors**: Multiple components (`runefoble-board.ts`, `runefoble-character-card.ts`, `runefoble-app.ts`, `runefoble-initiative-tracker.ts`) include hardcoded hex colors (e.g., `#121212`, `#ffffff`, `#4b5563`, `#f8f9fa`), resulting in unreadable text, broken borders, or invisible shadows when theme or mode changes.
3. **Black-on-Black Shadows in Dark Mode**: Hard drop-shadows like `4px 4px 0px #121212` are completely invisible on dark canvas surfaces (`#121212`, `#0f172a`), erasing the tactile neobrutalist depth central to the design system.

## Governing Architecture & ADRs
- **ADR-0004**: Lit Web Components and Storybook UI (CSS token inheritance in Shadow DOM).
- **ADR-0012**: Design System Theming Tokens & Bauhaus Modernist Aesthetic.
- **Hard Invariant 3**: Storybook stories verify visual presentation across all mode/theme permutations.
- **Hard Invariant 6**: File length limit (<500 lines) strictly respected across all files.
- **Hard Invariant 7**: Blackbox TDD verification through token definitions and rendered component styles.

## Key Changes & Specifications

### 1. Semantic Token Hierarchy (`frontend/src/styles/themes.css`)
Refactor `themes.css` to provide a complete layer of semantic tokens parameterized by both `data-theme` and `data-color-mode`:
- **Surfaces & Elevation**:
  - `--rf-bg-canvas`: Base viewport background.
  - `--rf-bg-surface`: Main structural panel/container background.
  - `--rf-bg-surface-elevated`: Floating modals, dropdowns, and overlays.
  - `--rf-bg-card`: Tactical cards, feed items, and token detail panels.
  - `--rf-bg-inset`: Recessed areas (input boxes, dice tray wells).
- **Text & Contrast Hierarchy**:
  - `--rf-text-primary`: Primary headings, body copy, and high-emphasis stats (min 7:1 contrast).
  - `--rf-text-secondary`: Section titles, timestamps, and labels (min 4.5:1 contrast).
  - `--rf-text-muted`: Placeholder hints, disabled states, and secondary metadata.
  - `--rf-text-inverse`: Text displayed on opposite-contrast accent fills.
- **Borders & Dividers**:
  - `--rf-border-color`: Primary structural border (dark ink in light mode, high-contrast crisp border in dark mode).
  - `--rf-border-subtle`: Internal dividers, grid cell lines, and table rows.
  - `--rf-border-focus`: High-visibility focus ring color for keyboard navigation.
- **Shadows & Tactile Elevation**:
  - `--rf-shadow-color`: Dynamic shadow tone (`rgba(18, 18, 18, 1)` in light mode, contrasting dark edge or subtle ambient glow in dark mode).
  - `--rf-shadow`: `var(--rf-border-width, 2px) var(--rf-border-width, 2px) 0px var(--rf-shadow-color)`.
  - `--rf-shadow-sm`: `1px 1px 0px var(--rf-shadow-color)`.

### 2. Full Theme Matrix (Theme × Color Mode)
Define explicit token sets for both light and dark variations across all 4 core themes:
1. **Bauhaus Modernist**:
   - *Light*: Clean warm off-white canvas (`#f8f9fa`), deep ink black borders (`#121212`), primary cadmium red (`#e63946`), cobalt blue (`#1d3557`), canary yellow (`#ffb703`).
   - *Dark*: Deep charcoal canvas (`#121212`), elevated surfaces (`#1e1e1e`), crisp light borders (`#f8f9fa`), brightened primary accents for dark contrast.
2. **Dark Fantasy**:
   - *Dark*: Obsidian canvas (`#0f172a`), runic purple (`#8b5cf6`), amber gold (`#f59e0b`), slate borders (`#334155`).
   - *Light*: Illuminated parchment cathedral theme with gothic stone borders and stained-glass accents.
3. **Parchment**:
   - *Light*: Sunlit aged paper (`#f4ecd8`), antique crimson (`#9b2226`), sepia ink text (`#2e1b0f`), brass accents.
   - *Dark*: Candlelit desk study (`#2b1d14`), warm glow surfaces (`#3a281c`), light parchment ink (`#f4ecd8`).
4. **Cyber Rune**:
   - *Dark*: Void black canvas (`#09090b`), neon cyan (`#06b6d4`), magenta (`#ec4899`), luminous grid glow.
   - *Light*: Clean high-tech blueprint canvas (`#f0f9ff`), electric cyan borders, deep indigo text.

### 3. Comprehensive Web Component Audit & Hardcoded Color Removal
Replace all hardcoded hex literals with CSS tokens across all components:
- `frontend/src/runefoble-app.ts`: Header borders, background, spectator badge, voice panel styling.
- `frontend/src/components/runefoble-board.ts`: Tactical grid coordinates, cell borders, fog-of-war shroud opacity and colors, token badges.
- `frontend/src/components/runefoble-character-card.ts`: HP bars, AC shield badge, condition pills, spell slot circles.
- `frontend/src/components/runefoble-watcher-feed.ts`: Event card backgrounds, speaker tags, narrative vs speech styling.
- `frontend/src/components/runefoble-dice-roller.ts`: Tray well background, dice face rendering, result total banner.
- `frontend/src/components/runefoble-initiative-tracker.ts`: Active combatant highlight, countdown progress bar, next-turn badge.
- `frontend/src/components/runefoble-spectator-view.ts`: Atmosphere banner, chronicle clean overlay.
- `frontend/src/components/runefoble-absentee-recap.ts`: Recap entry cards, audio scrub bar, penalty badges.

### 4. Verification & Storybook Stories
- Update `frontend/.storybook/preview.ts` to include interactive Dark / Light mode switching in the Storybook toolbar.
- Add Storybook test matrix rendering components side-by-side in both Light and Dark modes.
- Extend `tests/test_theming.py` to verify:
  - Complete semantic token coverage for all themes under both `[data-color-mode="light"]` and `[data-color-mode="dark"]`.
  - Zero hardcoded hex color literals in Web Component `static styles` blocks (using regex AST inspection).
  - All files satisfy the <500 lines invariant.

## Definition of Done (Checkable Deliverables)
1. Semantic tokens (`--rf-bg-canvas`, `--rf-bg-surface`, `--rf-text-primary`, `--rf-border-color`, `--rf-shadow-color`, etc.) defined for all themes in both light and dark modes in `themes.css`.
2. All 8 core Lit components audited with zero hardcoded hex colors remaining in Shadow DOM style blocks.
3. Shadows in dark mode remain visually distinct and tactile (avoiding invisible black-on-black).
4. Storybook toolbar updated with Light / Dark switcher; all stories render legibly without contrast issues.
5. Automated test suite in `tests/test_theming.py` expanded and passing 100%.
6. All source files strictly under 500 lines.
