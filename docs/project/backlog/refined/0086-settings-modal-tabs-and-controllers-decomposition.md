---
id: '0086'
title: Settings Modal Tab Panels and Sub-Controllers Modular Decomposition
status: refined
created: 2026-09-26
dependencies:
- TASK-0012
- TASK-0073
- TASK-0074
governing_adrs:
- ADR-0004
- ADR-0012
- ADR-0013
target_release: 0.2.0
---

# TASK-0086: Settings Modal Tab Panels and Sub-Controllers Modular Decomposition

## Status
Refined

## Summary
Decompose `frontend/src/components/runefoble-settings-modal.ts` (420 lines, 84.0% of limit) by extracting tab view panels (`runefoble-settings-appearance.ts`, `runefoble-settings-audio.ts`, `runefoble-settings-dice.ts`) into dedicated subcomponents to ensure strict adherence to Hard Invariant 6 (File length limit < 500 lines).

## Problem Statement
Health scans identify `frontend/src/components/runefoble-settings-modal.ts` at 420 lines, approaching the 500-line hard invariant ceiling.
`runefoble-settings-modal.ts` was introduced in TASK-0073 to provide unified configuration across theme selection, dark/light mode toggling, audio device selection, and dice physics options. While styles were extracted into `runefoble-settings-modal.styles.ts`, the component file itself bundles:
1. Modal backdrop, keyboard accessibility trap (Escape/Tab), focus restoration, and dialog layout.
2. Appearance tab DOM rendering: Theme selection grid, radio chips, and color mode (Light/Dark/System) switcher.
3. Audio settings tab DOM rendering: Device selector dropdown, noise suppression toggles, and state dispatch.
4. Dice settings tab DOM rendering: 3D physics toggle, audio feedback toggles, and roll test buttons.

As future settings (e.g. spectator overlay preferences, subtitle toggles, AI DM verbosity) are added, this component will exceed 500 lines without modular decomposition into dedicated subview panels.

## Governing Architecture & ADRs
- **ADR-0004**: Lit Web Components and Storybook UI (Shadow DOM encapsulation and isolated subviews).
- **ADR-0012**: Design System Theming Tokens & Bauhaus Modernist Aesthetic.
- **ADR-0013**: Microfrontend Architecture and Service Component Vendoring.

## Proposed Decomposition
1. **Appearance Tab Panel (`frontend/src/components/settings/runefoble-settings-appearance.ts`)**:
   - Encapsulates theme selection buttons, color mode toggles, and theme preview cards (< 120 lines).
2. **Audio Tab Panel (`frontend/src/components/settings/runefoble-settings-audio.ts`)**:
   - Encapsulates audio device select dropdown, noise suppression toggles, and microphone permission indicators (< 100 lines).
3. **Dice Tab Panel (`frontend/src/components/settings/runefoble-settings-dice.ts`)**:
   - Encapsulates 3D physics toggles, sound effect switches, and test roll buttons (< 90 lines).
4. **Settings Modal Coordinator (`frontend/src/components/runefoble-settings-modal.ts`)**:
   - Lightweight dialog wrapper managing active tab state, focus trap, and dispatching global settings events (< 140 lines).

## INVEST Criteria Evaluation
- **Independent (I)**: Decomposes internal component views without modifying the `<runefoble-settings-modal>` Custom Element tag, properties, or public CustomEvents.
- **Negotiable (N)**: Subcomponent directory layout (`frontend/src/components/settings/` vs sibling files) can be adjusted.
- **Valuable (V)**: Protects against Hard Invariant 6 violations (< 500 lines) and enables clean scalability as more settings tabs are introduced.
- **Estimable (E)**: Standard Web Component decomposition into child Lit elements with Shadow DOM encapsulation.
- **Small (S)**: Scope strictly isolated to `frontend/src/components/runefoble-settings-modal.ts`; all resulting files < 150 lines.
- **Testable (T)**: Storybook stories (`frontend/src/stories/runefoble-settings-modal.stories.ts`), TypeScript compilation (`pnpm run build`), and component tests verify identical functionality.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Modular Subcomponent Extraction**:
   - `runefoble-settings-modal.ts` decomposed into focused subcomponents strictly under 150 lines each.
2. **File Length Compliance (Hard Invariant 6)**:
   - All touched and newly created files strictly under 150 lines.
3. **Public Custom Element Contract**:
   - Preserves identical `<runefoble-settings-modal>` public contract, properties (`open`, `currentTheme`, `currentColorMode`), and events (`theme-changed`, `color-mode-changed`).
4. **Storybook Verification**:
   - 100% Storybook verification across all tabs with zero console errors.
5. **Frontend Build**:
   - Passes `pnpm run build` with zero TypeScript compiler errors.
