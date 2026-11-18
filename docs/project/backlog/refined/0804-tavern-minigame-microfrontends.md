---
id: '0804'
title: "Tavern Minigame Microfrontends: Darts, Liar's Dice and Roulette"
status: Refined
created: 2026-11-18
dependencies: []
governing_adrs:
- ADR-0004
- ADR-0013
- ADR-0014
governing_prds:
- PRD-0024
governing_stories:
- US-0047
- US-0074
target_bc: game_session
target_release: 0.9.0
---

# TASK-0804: Tavern Minigame Microfrontends: Darts, Liar's Dice and Roulette

## Status
Refined. Found during batch 26 to 28 integration, 2026-11-18.

## Summary
The game_session manifest advertised `runefoble-minigame-darts`, `runefoble-minigame-liars-dice` and `runefoble-minigame-roulette`, but no such components exist. TASK-0711 removed them from the manifest.

## Problem Statement
- No Lit components exist in `services/game_session/ui/src/` for these tags.

## Documentation & Architecture Review
- AGENTS.md hard invariants and DoR 9 (no compatibility shims).
- ADR-0004, ADR-0013, ADR-0014.

## Product & User Story References
PRD-0024, US-0047, US-0074

## Detailed Specification & Implementation Plan
1. Build each component in `services/game_session/ui/src/` with Shadow DOM and Bauhaus tokens, driven by the existing minigame routes and socket.
2. Add Storybook stories with zero console errors.
3. Add the tags back to the game_session manifest.
4. Add Playwright BDD scenarios from US-0074.

## Frontdoor Blackbox Test Plan
- Vitest browser tests for each component.
- A manifest test that each advertised tag is defined.
- Playwright BDD scenarios from US-0074.

## Definition of Done
- The test plan passes.
- `make test`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: medium
- Source audits: TASK-0711 (Discovered)
