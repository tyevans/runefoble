---
id: '0761'
title: The App Shell Routes Mesh Messages to Typed Microfrontend Entry Points
status: Complete
created: 2026-11-17
dependencies:
- TASK-0643
governing_adrs:
- ADR-0013
- ADR-0004
governing_prds:
- PRD-0005
- PRD-0023
governing_stories:
- US-0014
target_bc: frontend
target_release: 0.9.0
---
# TASK-0761: The App Shell Routes Mesh Messages to Typed Microfrontend Entry Points

## Status
Complete

## Summary
The shell searches the shadow roots of service elements and sets their internal fields. Each owner must expose one public entry point. The shell forwards messages by type and does not read shadow DOM.

## Problem Statement
- `frontend/src/vtt-mesh-handlers.ts:12-21` (`getMountedPluginElement`) searches shadow roots of plugin slots.
- `:30`, `:43`, `:48`, `:58` query `runefoble-board` and call `roll3DDice`, `triggerSpellVFX`, `handleIncomingSocketMessage`, and set `activeAoE`, `activeTurnTokenId`.
- `:21-25` sets `forcedResult` on the dice roller and fields on the initiative tracker.
- `frontend/src/runefoble-app.ts:195` reads the header shadow DOM to restore focus.
- `as any` casts hide all of it from the compiler.

## Documentation & Architecture Review
- ADR-0013 point 1 (the shell multiplexes events to microfrontends) and the negative consequences (no direct internal state references). TASK-0643 splits the app into view controllers. Do this after it.
- Overlap: TASK-0649 changes E2E steps only. TASK-0685 changes mounting only.

## Product & User Story References
- PRD-0005. PRD-0023. US-0014.

## Detailed Specification & Implementation Plan
1. Each owner exposes one typed method `handleMeshMessage(msg: MeshMessage)`: `runefoble-board`, `runefoble-dice-roller`, `runefoble-initiative-tracker`, `runefoble-dice-tray-3d`. Types live in the owner package.
2. The shell keeps a map from message type to target tag, and calls the method on the element it mounted (it holds the reference, no shadow search).
3. `vtt-mesh-handlers.ts` becomes this router. Remove every `as any` and `getMountedPluginElement`.
4. Replace the focus restore in `runefoble-app.ts:195` with a `focus-restore` method on the header element.

## Frontdoor Blackbox Test Plan
- Playwright BDD on the live board: send dice roll, turn advance, AoE placement and spell VFX through the session WebSocket. Assert the visible result for each. No shadow DOM query in the steps.

## Definition of Done
- `frontend/src` has no shadow-root reads of service elements. Count of `as any` in the changed files is zero.
- Docs updated. Gates pass. No file over 500 lines.

## Audit Provenance
- Severity: medium
- Source audits: `frontend-ui`
