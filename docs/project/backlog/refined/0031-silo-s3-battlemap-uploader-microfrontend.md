---
id: 0031
title: Silo S3 Battlemap Asset Uploader & Shroud Masking in Board State Microfrontend
status: Refined
created: 2026-09-25
dependencies: [TASK-0023, TASK-0026]
governing_adrs: [ADR-0004, ADR-0012, ADR-0013]
target_release: 0.1.0
---

# TASK-0031: Silo S3 Battlemap Asset Uploader & Shroud Masking in Board State Microfrontend

## Status
Refined (Ready to pull)

## Summary
Add a battlemap asset uploader component (`<runefoble-map-uploader>`) to `@runefoble/board-state-ui` allowing GMs to drag-and-drop tactical map images directly onto the board. Integrates with the platform's Silo S3 storage pipeline (`/api/v1/assets/upload`) and automatically applies dynamic fog-of-war shroud masking.

## Scope & Architectural Impact
- Service Bounded Context: `services/board_state/ui/`
- Component: `<runefoble-map-uploader>`
- Supports image upload, progress bar, presigned URL preview, and grid alignment sliders.
- Emits `@map-uploaded` CustomEvent containing asset ID and resolution metadata.
- Exported via `@runefoble/board-state-ui` and registered in `GET /ui/manifest`.

## Definition of Ready Checklist
- [x] Bounded context ownership verified (`services/board_state/ui/`).
- [x] Governing ADRs cited (ADR-0004, ADR-0012, ADR-0013).
- [x] Testable blackbox acceptance criteria established.
- [x] Storybook stories planned (Empty dropzone, Uploading progress, Aligned map preview).

## Definition of Done
1. Component created in `services/board_state/ui/src/runefoble-map-uploader.ts`.
2. Interactive Storybook stories added in `services/board_state/ui/src/runefoble-map-uploader.stories.ts` with zero console errors.
3. Registered in `services/board_state/src/board_state/main.py` under `/ui/manifest`.
4. Frontdoor blackbox tests in `tests/test_microfrontends.py` verify upload and event dispatching.
5. `make test` and `make lint` pass cleanly.
6. File length strictly under 500 lines.
