---
id: '0078'
title: Battlemap Uploader Subviews and Grid Controller Modular Decomposition
status: Proposed
created: 2026-09-26
dependencies: [TASK-0023, TASK-0031]
governing_adrs: [ADR-0004, ADR-0012, ADR-0013]
target_release: 0.2.0
---

# TASK-0078: Battlemap Uploader Subviews and Grid Controller Modular Decomposition

## Status
Proposed

## Summary
Decompose `services/board_state/ui/src/runefoble-map-uploader.ts` (315 lines, 63.0% of limit) into focused subcomponents for drag-and-drop file ingestion and interactive tactical grid/shroud masking configuration to prevent breaching Hard Invariant 6 (File length limit < 500 lines) as procedural battlemap generation (TASK-0049) and universal VTT imports (TASK-0057) land.

## Problem Statement
`runefoble-map-uploader.ts` currently couples two distinct responsibilities within a single component:
1. Drag-and-drop file dropzone, MIME validation, multipart Silo S3 HTTP uploading, progress bar animation, and error alerting.
2. Tactical grid calibration, dynamic canvas overlay rendering, coordinate resolution calculation, and cell-by-cell fog-of-war shroud masking controls.

As upcoming roadmap features introduce procedural battlemap generation from AI prompts (TASK-0049) and Universal VTT file importing with light/wall metadata (TASK-0057), this component will grow beyond 500 lines unless decomposed into modular, reusable subcomponents.

## Proposed Decomposition
1. **Dropzone & Upload Sub-controller (`services/board_state/ui/src/runefoble-map-dropzone.ts`)**:
   - Encapsulate file drag/drop listeners, file input handling, and upload progress dispatch (< 130 lines).
2. **Shroud & Grid Configuration Sub-controller (`services/board_state/ui/src/runefoble-map-grid-config.ts`)**:
   - Encapsulate grid column/row sliders, opacity controls, reveal all/shroud all actions, and cell toggle logic (< 140 lines).
3. **Primary Coordinator Component (`services/board_state/ui/src/runefoble-map-uploader.ts`)**:
   - Thin Lit orchestrator managing high-level state and dispatching the `map-uploaded` CustomEvent (< 120 lines).

## INVEST Criteria Evaluation
- **Independent (I)**: Decomposes internal microfrontend component architecture without modifying the `<runefoble-map-uploader>` Custom Element tag, attributes, or `map-uploaded` event detail contract.
- **Negotiable (N)**: Distribution of grid preview canvas rendering can be adjusted between components.
- **Valuable (V)**: Protects against Hard Invariant 6 violations (< 500 lines) and enables reuse of dropzone and grid calibration UI across asset forge and VTT importer tools.
- **Estimable (E)**: Standard Web Component decomposition into subview modules with Shadow DOM encapsulation.
- **Small (S)**: Scope strictly isolated to `services/board_state/ui/src/runefoble-map-uploader.ts`; all resulting files < 150 lines.
- **Testable (T)**: Verified via Storybook stories, `pnpm run build` TypeScript compilation, and `uv run pytest tests/test_microfrontends.py tests/test_blackbox_silo_assets.py`.

## Acceptance Criteria
1. `runefoble-map-uploader.ts` decomposed into focused subcomponents strictly under 150 lines each.
2. 100% Storybook verification with zero console errors.
3. Preserves identical `<runefoble-map-uploader>` element contract, properties, and `map-uploaded` event payload.
4. Conforms strictly to Hard Invariant 6 (< 500 lines per file).
