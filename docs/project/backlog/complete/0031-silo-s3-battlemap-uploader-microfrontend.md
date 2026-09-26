---
id: 0031
title: Silo S3 Battlemap Asset Uploader & Shroud Masking in Board State Microfrontend
status: Complete
created: 2026-09-25
completed: 2026-09-26
dependencies: [TASK-0023, TASK-0026]
governing_adrs: [ADR-0004, ADR-0012, ADR-0013]
target_release: 0.1.0
---

# TASK-0031: Silo S3 Battlemap Asset Uploader & Shroud Masking in Board State Microfrontend

## Status
Complete

## Summary
Added a battlemap asset uploader component (`<runefoble-map-uploader>`) to `@runefoble/board-state-ui` allowing GMs to drag-and-drop tactical map images directly onto the board. Integrates with the platform's Silo S3 storage pipeline (`/api/v1/assets/upload`) and automatically applies dynamic fog-of-war shroud masking.

## Key Changes
- Created component in `services/board_state/ui/src/runefoble-map-uploader.ts`:
  - Drag-and-drop zone and file picker for tactical map images.
  - Upload integration with `/api/v1/assets/upload` with progress bar and feedback.
  - Presigned/object URL preview with dynamic fog-of-war shroud overlay and interactive cell revelation.
  - Grid alignment sliders for columns, rows, grid opacity, and shroud opacity.
  - Emits `@map-uploaded` CustomEvent with asset ID, download URL, dimensions, and grid/shroud configuration.
- Created interactive Storybook stories in `services/board_state/ui/src/runefoble-map-uploader.stories.ts` (`EmptyDropzone`, `UploadingProgress`, `AlignedMapPreview`, `FogOfWarMasked`).
- Exported from `@runefoble/board-state-ui` in `services/board_state/ui/src/index.ts` and created forwarding re-export in `frontend/src/components/runefoble-map-uploader.ts`.
- Registered `runefoble-map-uploader` under `/ui/manifest` in `services/board_state/src/board_state/main.py`.
- Updated frontdoor blackbox test suite in `tests/test_microfrontends.py` to verify `/ui/manifest`, Silo S3 asset upload frontdoor, component contract, and stories.
- Updated Diataxis reference documentation in `docs/reference/microfrontend-architecture.md`.

## Verification
- `uv run pytest` passes cleanly with all tests passing.
- `make build` verifies frontend and Storybook static builds pass without errors.
- `make lint` passes typechecking and lint checks.
