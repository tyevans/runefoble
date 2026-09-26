---
id: 0012
title: Frontend Theming System with Bauhaus Modernist Default
status: Complete
created: 2026-09-25
completed: 2026-09-25
dependencies: [TASK-0004, TASK-0010]
governing_adrs: [ADR-0004, ADR-0012]
target_release: 0.1.0
governing_prds:
- PRD-0003
governing_stories:
- US-0012
---

# TASK-0012 — Frontend Theming System with Bauhaus Modernist Default

## Status
Complete

## Summary
Implemented a design token theming architecture across the Runefoble Lit Web Component frontend (US-0016, ADR-0012). The default theme is **Bauhaus Modernism**, characterized by bold primary color blocks (cadmium red `#e63946`, cobalt blue `#1d3557`, canary yellow `#ffb703`), deep ink black borders (`2px solid #121212`), high-contrast off-white canvas (`#f8f9fa`), clean geometric sans typography, and offset solid drop-shadows (`4px 4px 0px #121212`). Also provided support for alternate themes (`dark-fantasy`, `parchment`, `cyber-rune`), an interactive `<runefoble-theme-switcher>` component with localStorage persistence, and Storybook stories demonstrating all theme variations.

## Key Changes
1. **Design Tokens & Theme Styles (`frontend/src/styles/themes.css`, `frontend/src/index.css`)**:
   - Defined CSS custom properties on `:root` and `[data-theme="bauhaus"]` for colors, surfaces, borders, radii, and hard drop-shadows.
   - Defined alternate themes for `[data-theme="dark-fantasy"]` (Obsidian canvas `#0f172a`, rune purple `#8b5cf6`, gold `#f59e0b`), `[data-theme="parchment"]` (aged paper `#f4ecd8`, crimson `#9b2226`, brass `#bb8524`), and `[data-theme="cyber-rune"]` (neon dark `#09090b`, cyan `#06b6d4`, pink `#ec4899`).
   - Imported `themes.css` into `frontend/src/index.css` and `frontend/src/runefoble-app.ts`.
2. **Theme Switcher Component (`frontend/src/components/runefoble-theme-switcher.ts`, `frontend/src/index.ts`)**:
   - Built `<runefoble-theme-switcher>` with bold Bauhaus buttons, active selection badges, localStorage persistence, and `theme-changed` CustomEvent dispatch.
   - Sets `document.documentElement.setAttribute('data-theme', theme)` on initialization and runtime switching.
   - Exported from `frontend/src/index.ts`.
3. **Lit Components Token Inheritance**:
   - Updated `frontend/src/runefoble-app.ts` to embed the theme switcher in the header and adopt `--rf-*` canvas, text, and border tokens.
   - Updated `frontend/src/components/runefoble-board.ts`, `frontend/src/components/runefoble-character-card.ts`, and `frontend/src/components/runefoble-watcher-feed.ts` to inherit `--rf-*` CSS tokens.
4. **Storybook Stories (`frontend/src/stories/theme-switcher.stories.ts`, `frontend/.storybook/preview.ts`)**:
   - Created interactive stories for Bauhaus, Dark Fantasy, Parchment, and Cyber Rune contexts.
   - Imported `themes.css` into Storybook preview.
5. **Tests & Quality (`tests/test_theming.py`)**:
   - Added automated tests verifying CSS variable definitions, alternate themes, component properties, element exports, and file line length limits.

## Verification
- `uv run pytest tests/test_theming.py`: 7/7 passed.
- `uv run pytest`: 96/96 passed across the entire suite.
- `uv run ruff check .`: Clean, 0 errors.
- `cd frontend && pnpm run build`: TypeScript compile and Vite bundle passed.
- `cd frontend && pnpm run build-storybook`: Storybook build passed in 595ms.
- All files strictly satisfy file length limit (<500 lines).
