---
id: '0648'
title: App Shell Composes Rules Compendium and Removes Orphaned Microfrontend Imports
status: Refined
created: 2026-11-17
dependencies:
- TASK-0643
- TASK-0502
governing_adrs:
- ADR-0004
- ADR-0013
governing_prds:
- PRD-0008
- PRD-0023
governing_stories:
- US-0037
- US-0052
target_release: 0.9.0
---

# TASK-0648: App Shell Composes Rules Compendium and Removes Orphaned Microfrontend Imports

## Status
Refined

## Summary
Several microfrontends are declared or imported but never mounted. The rules compendium package is in `frontend/package.json`, yet no route renders it. Six forwarding modules have no importer. Some frontend-local components have no runtime use. Compose the rules compendium on a route, and delete the orphaned components and their stories. Soundscape composition, the lore atlas, and the minigames are excluded here because TASK-0437, TASK-0446, TASK-0452, and TASK-0371 to TASK-0372 cover them.

## Problem Statement
- `w2-app-shell.md` F8: `frontend/package.json` declares `@runefoble/rules-compendium-ui`, but no route composes it. The App Shell has only a forwarding file for it.
- `w2-app-shell.md` F8: these components have no runtime usage (grep of `frontend/src` and `services/*/ui/src`, excluding stories): `runefoble-bulletin-board.ts`, `minigames/runefoble-merchant-haggler.ts`, `minigames/runefoble-minigame-darts.ts`, `minigames/runefoble-minigame-liars-dice.ts`, `minigames/runefoble-minigame-roulette.ts`, and `dm-controls/runefoble-dm-negotiation-drawer.ts`.
- Six forwarding modules have zero importers: `runefoble-absentee-vote-card.ts`, `runefoble-faction-espionage.ts`, `runefoble-faction-radar.ts`, `runefoble-mobile-companion.ts`, `runefoble-vocal-modulator.ts`, and `runefoble-voice-duplex-controls.ts`. These are forwarders, so TASK-0502 removes them.
- `w2-rules-compendium.md` also reports that the App Shell's rules compendium forwarder is a shim (TASK-0502 removes it).

## Documentation & Architecture Review
- `docs/how-to/balance-combat-encounters-and-query-compendium.md` describes the compendium. Its App Shell instructions must name the route.
- DoR 9: the forwarders go. Do not replace them with new re-exports.
- ADR-0013: the shell imports each package root only. Components that have no route are not imported.
- Note: the rules compendium gateway route is not in `gateway/api` (see `w2-rules-compendium.md`). This task must not compose the compendium against a missing route. The composition depends on the gateway proxy, which is handled by the rules-compendium synthesis theme. Confirm that proxy exists before merging.

## Product & User Story References
- [`prd-0008-ttrpg-rules-compendium-and-encounter-builder.md`](../../product/accepted/prd-0008-ttrpg-rules-compendium-and-encounter-builder.md)
- [`us-0037-automated-cr-encounter-balancing-and-compendium.md`](../../user_stories/accepted/us-0037-automated-cr-encounter-balancing-and-compendium.md)
- [`us-0052-homebrew-spell-monster-and-rule-authoring.md`](../../user_stories/accepted/us-0052-homebrew-spell-monster-and-rule-authoring.md)

## Detailed Specification & Implementation Plan
1. Add a route `#/rules` (or a campaign tab, decided at refinement) that mounts `<runefoble-rules-compendium>` and `<runefoble-encounter-builder>` from the package root.
2. Delete the orphaned frontend-local components listed above, with their stories and tests. The six forwarding modules are deleted by TASK-0502, not here. Remove any import of a deleted file from `frontend/src/index.ts`. Do not touch the other forwarders.
3. Remove `@runefoble/rules-compendium-ui` from `frontend/package.json` only if it is no longer imported; otherwise keep it.
4. Add a check to `frontend/` that fails when a `*.ts` file under `frontend/src/components` has no importer (excluding `index.ts` and stories). Run it in `pnpm run lint`.
5. Record in the task file which orphans were deleted, so later audits do not recreate them.

## Frontdoor Blackbox Test Plan
Playwright BDD (`e2e/features/rules_compendium_route.feature`):
- Scenario: A player searches the compendium and sees a monster.
  - Given the signed-in player opens the rules route
  - When the player searches "goblin"
  - Then the results list contains "Goblin" from the public compendium route.
- Before the change the route does not exist and the scenario FAILS. After the change it PASSES.
- The orphan check is a unit test in `frontend/test/no-orphan-components.test.ts`. It is a repository check, not a behaviour test.

## Definition of Done
1. The rules compendium is reachable from the App Shell through its route, and the BDD scenario passes.
2. The listed orphan components are deleted, with their stories and tests. The forwarders are left to TASK-0502.
3. The orphan check passes in `pnpm run lint`.
4. Storybook builds with zero console errors for every remaining story.
5. `pnpm run build` passes. Changelog entry under `[Unreleased]`.
6. The task file lists every deleted path.

## Audit Provenance

- Severity: medium
- Source audits: `w2-app-shell.md`, `w2-rules-compendium.md`

## Orchestrator Addenda (2026-11-17, refactor-r1)

- TASK-0648 (Evidence, append): "Six forwarding files have no importer: `runefoble-absentee-vote-card.ts`, `runefoble-faction-espionage.ts`, `runefoble-faction-radar.ts`, `runefoble-mobile-companion.ts`, `runefoble-vocal-modulator.ts`, `runefoble-voice-duplex-controls.ts` in `frontend/src/components/`. Delete them."
