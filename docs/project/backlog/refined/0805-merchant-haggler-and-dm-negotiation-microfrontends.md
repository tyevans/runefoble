---
id: '0805'
title: "Merchant Haggler and DM Negotiation Drawer Microfrontends"
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
- US-0075
- US-0047
target_bc: game_session
target_release: 0.9.0
---

# TASK-0805: Merchant Haggler and DM Negotiation Drawer Microfrontends

## Status
Refined. Found during batch 26 to 28 integration, 2026-11-18.

## Summary
The game_session manifest advertised `runefoble-merchant-haggler` and `runefoble-dm-negotiation-drawer`, but no such components exist. TASK-0711 removed them from the manifest.

## Problem Statement
- No Lit components exist in `services/game_session/ui/src/` for these tags.

## Documentation & Architecture Review
- AGENTS.md hard invariants and DoR 9 (no compatibility shims).
- ADR-0004, ADR-0013, ADR-0014.

## Product & User Story References
PRD-0024, US-0075, US-0047

## Detailed Specification & Implementation Plan
1. Build both components in `services/game_session/ui/src/` against the existing haggling routes. The DM drawer shows only to callers with DM permission (SpiceDB).
2. Add Storybook stories, re-advertise the tags, and add Playwright BDD scenarios from US-0075.

## Frontdoor Blackbox Test Plan
- Vitest browser tests for both components.
- Playwright BDD scenarios from US-0075.

## Definition of Done
- The test plan passes.
- `make test`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: medium
- Source audits: TASK-0711 (Discovered)
