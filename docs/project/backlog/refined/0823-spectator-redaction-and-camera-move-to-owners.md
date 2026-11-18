---
id: '0823'
title: "Spectator Redaction, Camera Direction and the OBS Overlay Move to Their Owners"
status: Refined
created: 2026-11-18
dependencies:
- TASK-0809
- TASK-0822
governing_adrs:
- ADR-0013
- ADR-0015
governing_prds: []
governing_stories: []
target_bc: game_session
target_release: 0.9.0
---

# TASK-0823: Spectator Redaction, Camera Direction and the OBS Overlay Move to Their Owners

## Status
Refined

## Summary
The gateway holds redaction rules, camera math and overlay HTML, which are domain and presentation logic.

## Problem Statement
- Findings G-07, G-11, G-13 in `.audit/research/gateways.md` give every location (path:line). Check each against main before you change it.

## Documentation & Architecture Review
- AGENTS.md (SOLID, DDD, Hard Invariants 1, 2, 6, 7; DoR 9: no shims or aliases).
- ADR-0013, ADR-0015.

## Product & User Story References
None. Refactor and consolidation chosen by the user on 2026-11-18.

## Detailed Specification & Implementation Plan
1. Move redaction to the owner read (game_session/board_state) and camera direction to its owner. Render the OBS overlay as a Lit component in its bounded context.
2. Delete dead gateway code (G-11) and duplicate route paths (G-13), updating callers.

## Frontdoor Blackbox Test Plan
- Spectator and overlay responses carry no DM-only field, served by the owner. Storybook story for the overlay component.

## Definition of Done
- The test plan passes. `make test`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: refactor
- Source audits: `.audit/research/gateways.md` (G-07, G-11, G-13)
