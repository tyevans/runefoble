---
id: 0025
title: Microfrontend Architectural Governance and Workspace Configuration
status: Complete
created: 2026-09-25
completed: 2026-09-26
dependencies: [TASK-0024]
governing_adrs: [ADR-0004, ADR-0012, ADR-0013]
target_release: 0.1.0
---

# TASK-0025: Microfrontend Architectural Governance and Workspace Configuration

## Status
Complete

## Summary
Formulated and adopted **ADR-0013: Microfrontend Architecture and Service Component Vendoring**, establishing standard W3C Lit Custom Elements with Shadow DOM encapsulation as the platform microfrontend substrate. Configured root monorepo `pnpm-workspace.yaml` and `package.json` to link the lightweight App Shell with service microfrontend packages (`@runefoble/<bc>-ui`) via the `workspace:*` protocol.

## Key Changes
- `docs/project/adrs/accepted/adr-0013-microfrontend-architecture-and-service-component-vendoring.md`:
  - Authored ADR-0013 covering vertical slice domain ownership, Shadow DOM encapsulation, CSS variable penetration for Bauhaus themes, App Shell event orchestration, and workspace linkage.
- `docs/project/adrs/REGISTRY.md`:
  - Registered ADR-0013 in the sequential ADR register.
- `pnpm-workspace.yaml` & `package.json` (root):
  - Created root monorepo workspace configuration declaring `frontend` and `services/*/ui` packages with build approval for `esbuild`.
- `frontend/package.json`:
  - Added dependencies on `@runefoble/board-state-ui`, `@runefoble/character-sheet-ui`, `@runefoble/game-session-ui`, `@runefoble/the-watcher-ui`, and `@runefoble/voice-agent-ui`.

## Verification
- `pnpm install` links all 7 workspace packages without error.
- Verified workspace resolution via `make lint`.
