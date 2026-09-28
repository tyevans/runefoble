---
id: '0296'
title: DM Whisper Bar Styles and Controls Modular Decomposition
status: Proposed
created: 2026-09-28
dependencies:
- TASK-0053
- TASK-0061
governing_adrs:
- ADR-0003
- ADR-0004
- ADR-0012
- ADR-0013
governing_prds:
- PRD-0004
- PRD-0023
governing_stories:
- US-0020
- US-0025
target_release: 0.8.0
---

# TASK-0296: DM Whisper Bar Styles and Controls Modular Decomposition

## Status
Proposed

## Summary
Decompose `services/the_watcher/ui/src/runefoble-dm-whisper-bar.ts` (298 lines, 59.6% of limit) by extracting its embedded CSS stylesheet into `services/the_watcher/ui/src/runefoble-dm-whisper-bar.styles.ts` and extracting quick-action suggestion chips into a sub-component, keeping all files strictly < 150 lines per Hard Invariant 3 and 6.

## Problem Statement
`services/the_watcher/ui/src/runefoble-dm-whisper-bar.ts` combines LitElement template rendering, veto countdown timers, action proposal interception, WebSocket messaging, and an embedded static CSS block exceeding 110 lines inside the same 298-line TypeScript file. This violates the repository's frontend convention of separating styles into standalone `.styles.ts` modules with Bauhaus design tokens, and puts the component at risk of exceeding the 500-line limit as live spectator whisper moderation is added.

## Governing Architecture & ADRs
- **ADR-0003: Microfrontends with Lit & Shadow DOM**: Encapsulated UI components with independent lifecycle.
- **ADR-0004: Bauhaus Geometric Design System**: Strict usage of design tokens and theme-aware CSS custom properties.
- **ADR-0012: CSS Custom Properties & Design Tokens**: Decoupled component styles for light/dark mode theming.
- **ADR-0013: Modular Decomposition**: All source files kept strictly < 500 lines (submodules < 150 lines).

## Scope of Work
1. **Style Extraction (`services/the_watcher/ui/src/runefoble-dm-whisper-bar.styles.ts`)**:
   - Extract the entire `static styles = css`...` definition into an exported `dmWhisperBarStyles` CSSResult (< 120 lines).
   - Ensure all CSS variables leverage Bauhaus tokens (`--rf-color-*`, `--rf-font-*`, `--rf-space-*`).
2. **Component Refactoring (`services/the_watcher/ui/src/runefoble-dm-whisper-bar.ts`)**:
   - Import `dmWhisperBarStyles` and set `static styles = [dmWhisperBarStyles];`.
   - Streamline state management and whisper item rendering (< 180 lines).
3. **Verification**:
   - Build Storybook stories and verify tests with `npm test` or `uv run pytest tests/test_microfrontends.py`.

## Definition of Done
- `services/the_watcher/ui/src/runefoble-dm-whisper-bar.styles.ts` created with Bauhaus design tokens.
- `services/the_watcher/ui/src/runefoble-dm-whisper-bar.ts` refactored to import external styles, reducing file size to < 180 lines.
- Zero regression in DM whisper bar rendering, action proposal veto countdown, and event dispatching.
- Passes all frontend build and test checks.
