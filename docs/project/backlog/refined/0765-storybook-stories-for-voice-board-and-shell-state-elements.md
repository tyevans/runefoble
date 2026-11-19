---
id: '0765'
title: Storybook Stories for Voice, Board AoE and Shell Error Elements
status: Refined
created: 2026-11-17
dependencies: []
governing_adrs:
- ADR-0004
- ADR-0013
governing_prds:
- PRD-0019
- PRD-0020
governing_stories:
- US-0004
target_bc: voice_agent
target_release: 0.9.0
---
# TASK-0765: Storybook Stories for Voice, Board AoE and Shell Error Elements

## Status
Refined.

## Summary
Seven more custom elements have no story. Add them.

## Problem Statement
- `services/voice_agent/ui/src/duplex/settings_panel.ts`, `mobile_companion/audio_stream_controller.ts`, `mobile_companion/connection_status_badge.ts`, `mobile_companion/haptic_ping_panel.ts`, `runefoble-vocal-sliders.ts`.
- `services/board_state/ui/src/aoe_templates.ts`.
- `frontend/src/components/state/runefoble-data-error.ts`.
- Not included: `frontend/src/runefoble-app.ts` (the shell root; covered by Playwright route tests).

## Documentation & Architecture Review
- ADR-0004, ADR-0013, `docs/how-to/develop-lit-components-in-storybook.md`.

## Product & User Story References
- PRD-0019, PRD-0020. US-0004.

## Detailed Specification & Implementation Plan
1. One story file per element with default and failure states.
2. `runefoble-data-error` is a shell element. Put its story in `frontend/src/stories/`.

## Frontdoor Blackbox Test Plan
- `pnpm run build-storybook` succeeds. Zero console errors per story.

## Definition of Done
- Seven stories added. Storybook build clean. No file over 500 lines.

## Refactor r3 Addendum (Detailed Specification)

Refactor r3 addendum (2026-11-19): stories that stub `fetch` use `installStoryFetch` from `@runefoble/ui-core` (TASK-0921) and restore it in cleanup. Do not add a local fetch stub.

## Audit Provenance
- Severity: low
- Source audits: `frontend-ui`
