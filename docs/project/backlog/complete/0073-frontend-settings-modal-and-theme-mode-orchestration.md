---
id: '0073'
title: Frontend Settings Modal with Dark/Light/System Mode & Integrated Theme Switcher
status: Complete
created: 2026-09-25
dependencies:
- TASK-0012
- TASK-0072
governing_adrs:
- ADR-0004
- ADR-0012
target_release: 0.1.0
governing_prds:
- PRD-0013
governing_stories:
- US-0041
- US-0042
---
# TASK-0073 — Frontend Settings Modal with Dark/Light/System Mode & Integrated Theme Switcher

## Summary
Design and implement an accessible, tactile Bauhaus-modernist `<runefoble-settings-modal>` Web Component and migrate theme selection out of the top application header and into a centralized settings dialog. Introduce a global appearance mode switcher supporting **Dark**, **Light**, and **System** (OS `prefers-color-scheme` auto-detection), alongside integrated theme switching (`bauhaus`, `dark-fantasy`, `parchment`, `cyber-rune`), with persistent state and reactive DOM cascades.

## Context & Motivation
Currently, `<runefoble-theme-switcher>` is embedded directly in the main application header (`frontend/src/runefoble-app.ts`), consuming excessive horizontal screen real estate with individual theme buttons and lacking color mode (Dark vs. Light vs. System) management. Moving configuration to a unified settings modal declutters the header, creates a scalable home for upcoming audio/input preferences, and enables users to toggle between light and dark modes regardless of their selected genre theme.

## Governing Architecture & ADRs
- **ADR-0004**: Lit Web Components and Storybook UI (Shadow DOM encapsulation, reactive component state).
- **ADR-0012**: Design System Theming Tokens & Bauhaus Modernist Aesthetic.
- **Hard Invariant 3**: Component built and tested in Storybook first.
- **Hard Invariant 6**: File length limit (<500 lines) strictly preserved across all modules.
- **Hard Invariant 7**: Blackbox TDD verification with frontdoor DOM/event inspection.

## Key Changes & Specifications

### 1. Settings Trigger in Header (`frontend/src/runefoble-app.ts`)
- Replace the inline theme switcher in the header actions with a compact, Bauhaus-styled Settings button:
  - Icon: ⚙️ with label "Settings" or icon-only on mobile.
  - Proper ARIA attributes: `aria-haspopup="dialog"`, `aria-expanded="false/true"`, `aria-label="Open settings"`.
  - Clicking opens the `<runefoble-settings-modal>`.

### 2. Settings Modal Web Component (`frontend/src/components/runefoble-settings-modal.ts`)
- **Modal Dialog Architecture**:
  - Encapsulated backdrop overlay (`backdrop-filter: blur(4px); background: rgba(0, 0, 0, 0.6);`).
  - Dismissible via backdrop click, dedicated close button (✖), or `Escape` keyboard shortcut.
  - Focus trap and initial focus on modal open; restores focus to trigger on close.
- **Color Mode Controls (Dark / Light / System)**:
  - Segmented toggle control for:
    - ☀️ **Light**: Forces `data-color-mode="light"` on `document.documentElement`.
    - 🌙 **Dark**: Forces `data-color-mode="dark"` on `document.documentElement`.
    - 💻 **System**: Sets `data-color-mode="system"`, listening to `window.matchMedia('(prefers-color-scheme: dark)')` to dynamically cascade system dark/light preferences.
  - Persisted in `localStorage.getItem('runefoble-color-mode')` (defaults to `system`).
- **Theme Selection Cards**:
  - Migrated theme selection: `Bauhaus Modernist`, `Dark Fantasy`, `Parchment`, `Cyber Rune`.
  - Visual selection cards displaying theme name, icon badge, and primary palette swatch chips.
  - Persisted in `localStorage.getItem('runefoble-theme')` (defaults to `bauhaus`).
- **Extensible Settings Sections**:
  - Clean modular sections for `Appearance & Theme`, `Audio & Voice Input` (placeholder/device toggle), and `Dice & Physics`.
- **Event Dispatching**:
  - Emits `color-mode-changed` (`{ detail: { mode: 'light' | 'dark' | 'system', resolvedMode: 'light' | 'dark' } }`).
  - Emits `theme-changed` (`{ detail: { theme: string } }`).
  - Emits `settings-closed`.

### 3. Application Integration (`frontend/src/runefoble-app.ts`, `frontend/src/index.ts`)
- Embed `<runefoble-settings-modal>` at the top app level.
- Initialize both color mode and theme on app mount (`connectedCallback`), applying root attributes:
  `data-theme="<theme>"` and `data-color-mode="<mode>"`.
- Export `<runefoble-settings-modal>` from `frontend/src/index.ts`.

### 4. Storybook Stories (`frontend/src/stories/runefoble-settings-modal.stories.ts`)
- Stories demonstrating:
  - Default closed trigger.
  - Open modal in Light Mode.
  - Open modal in Dark Mode.
  - Active theme selection card states.
  - Storybook preview toolbar coordination.

## Definition of Done (Checkable Deliverables)
1. `<runefoble-settings-modal>` built in `frontend/src/components/runefoble-settings-modal.ts` with complete Shadow DOM styles using `--rf-*` tokens.
2. Inline theme switcher removed from `runefoble-app.ts` header; replaced with accessible Settings modal trigger button.
3. Dark, Light, and System modes fully functional, responding to system OS media queries when set to `system`.
4. Storybook stories running cleanly in `frontend/src/stories/runefoble-settings-modal.stories.ts` with zero console errors.
5. Unit and blackbox tests added in `tests/test_theming.py` or `tests/test_settings_modal.py` validating modal open/close lifecycle, keyboard escape, local storage sync, and custom event dispatches.
6. All touched files strictly under 500 lines.
