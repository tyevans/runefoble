---
id: '0502'
title: Remove Backward Compatibility Shims & Forwarding Exports in frontend
status: Complete
created: 2026-09-29
dependencies:
- TASK-0026
- TASK-0027
- TASK-0271
governing_adrs:
- ADR-0004
- ADR-0012
- ADR-0013
governing_prds:
- PRD-0001
- PRD-0023
governing_stories:
- US-0010
- US-0065
target_release: 0.9.0
---

# TASK-0502: Remove Backward Compatibility Shims & Forwarding Exports in frontend

## Status
Complete

Audit 2026-11-17: re-counted. There are 29 forwarders: 28 under `frontend/src/components/` (the 27 named in the Problem Statement plus `components/audience-studio.ts`) and `frontend/src/utils/dice.ts` (removed). Delete all 29 and list each by name before pull.

## Summary
Delete all 29 forwarding export components in `frontend/src/components/` created for "App Shell backwards compatibility", migrate any lingering App Shell imports directly to the vendored microfrontend packages (`@runefoble/*-ui`), and purge legacy fallback re-export assertions from frontend test suites.

## Problem Statement
When frontend components were decomposed into vendored service microfrontends (`services/<bc>/ui/`) per ADR-0013, 29 forwarding export files were left in `frontend/src/components/` purely for "App Shell backwards compatibility":
- `runefoble-absentee-recap.ts`, `runefoble-map-uploader.ts`, `runefoble-session-lobby.ts`, `runefoble-faction-espionage.ts`, `runefoble-watcher-feed.ts`
- `runefoble-audio-indicator.ts`, `runefoble-dm-trap-controls.ts`, `runefoble-character-sheet.ts`, `runefoble-voice-controls.ts`, `runefoble-spectator-view.ts`
- `runefoble-stand-in-guardrails.ts`, `runefoble-faction-radar.ts`, `runefoble-absentee-directive.ts`, `runefoble-autonomous-dm.ts`, `runefoble-dice-roller.ts`
- `runefoble-campaign-analytics.ts`, `runefoble-vocal-modulator.ts`, `runefoble-map-switcher.ts`, `runefoble-mobile-companion.ts`, `runefoble-combat-reaction-prompt.ts`
- `runefoble-soundscape-controls.ts`, `runefoble-board.ts`, `runefoble-initiative-tracker.ts`, `runefoble-rules-compendium.ts`, `runefoble-voice-duplex-controls.ts`
- `runefoble-character-card.ts`, `runefoble-absentee-vote-card.ts`
In addition, `frontend/test/app-data-service-decomposition.test.ts` actively tests legacy fallback data re-exports (`FALLBACK_CAMPAIGNS as LEGACY_FALLBACK_CAMPAIGNS`). Because there are no external consumers, retaining 29 wrapper files adds bloat, obscures the true microfrontend architecture, and violates DoR rule 9.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/how-to/develop-lit-components-in-storybook.md`: Microfrontend vendoring in `services/<bc>/ui/`.
  - `docs/how-to/orchestrate-app-shell-views-and-session-transitions.md`: Routed App Shell view orchestration.
- **Governing Architecture & ADRs**:
  - **ADR-0004: Lit Web Components and Storybook UI**: Shadow DOM encapsulation.
  - **ADR-0012: Frontend Application Shell**: Decoupled App Shell architecture.
  - **ADR-0013: Frontend Microfrontend Architecture**: Microfrontend component vendoring.

## Product & User Story References
- [`prd-0001-runefoble-platform-foundations.md`](../../product/accepted/prd-0023-unified-frontend-application-shell-and-campaign-hub.md)
- [`prd-0023-unified-frontend-application-shell-and-campaign-hub.md`](../../product/accepted/prd-0023-unified-frontend-application-shell-and-campaign-hub.md)
- `us-0010-developer-local-infrastructure-and-test-tooling.md`
- [`us-0065-routed-app-shell-views-and-session-transitions.md`](../../user_stories/accepted/us-0066-client-side-routing-navigation-and-breadcrumbs.md)

## Detailed Specification & Implementation Plan
1. **Delete All 29 Forwarding Export Components**:
   - Delete every forwarding wrapper file in `frontend/src/components/` that simply re-exports from `@runefoble/*-ui`.
2. **Audit and Update App Shell Imports**:
   - In `frontend/src/runefoble-app.ts`, `frontend/src/views/`, and Storybook stories, verify that all Custom Element registrations and components are imported directly from their owning microfrontend package (e.g., `@runefoble/the-watcher-ui`, `@runefoble/game-session-ui`, `@runefoble/board-state-ui`, etc.).
3. **Clean Up Test Assertions**:
   - In `frontend/test/app-data-service-decomposition.test.ts`, remove legacy fallback data re-export assertions (`LEGACY_FALLBACK_CAMPAIGNS`, `LEGACY_FALLBACK_CHARACTERS`).
   - In `frontend/test/radial-menu-decomposition.test.ts`, remove facade re-export parity assertions.
4. **Verify TypeScript and Storybook Builds**:
   - Run `pnpm exec tsc --noEmit` and `pnpm run build` in `frontend/` to confirm zero broken imports.

## INVEST Criteria Evaluation
- **Independent (I)**: Isolated cleanly to `frontend` App Shell package.
- **Negotiable (N)**: Clean TypeScript import standards.
- **Valuable (V)**: Eliminates 29 redundant wrapper files and enforces strict microfrontend decoupling.
- **Estimable (E)**: Exactly 29 known files to delete and specific test assertions to prune.
- **Small (S)**: File deletions and import cleanup.
- **Testable (T)**: Verified by `pnpm exec tsc --noEmit`, `pnpm test`, and `pnpm run build`.

## Definition of Done
1. All 29 forwarding export files in `frontend/src/components/` deleted.
2. All App Shell imports consume `@runefoble/*-ui` packages directly.
3. Obsolete legacy fallback re-export assertions removed from frontend tests.
4. Frontend typecheck (`pnpm exec tsc --noEmit`) and build (`pnpm run build`) pass cleanly.
5. Storybook stories build with zero missing module errors.

## Orchestrator Addenda (2026-11-17, refactor-r1)

- TASK-0502 (Evidence, append): "27 files in `frontend/src/components/` carry the text 'forwarding export for App Shell backwards compatibility'. Remove all of them and update importers."

## Orchestrator Addenda (2026-11-17, refactor-r1, ADR record)

- When this task lands, amend ADR-0013 point 4: remove "backward-compatible forwarding re-exports" from `frontend/src/components/`. That text conflicts with DoR 9.
