---
id: '0806'
title: "Bulletin Board and Campaign Telemetry Microfrontends"
status: Refined
created: 2026-11-18
dependencies: []
governing_adrs:
- ADR-0004
- ADR-0013
- ADR-0014
governing_prds:
- PRD-0024
- PRD-0012
governing_stories:
- US-0076
- US-0040
target_bc: game_session
target_release: 0.9.0
---

# TASK-0806: Bulletin Board and Campaign Telemetry Microfrontends

## Status
Refined. Found during batch 26 to 28 integration, 2026-11-18.

## Summary
`runefoble-bulletin-board` (game_session) and `runefoble-campaign-telemetry` (campaign_analytics) were advertised, but no such components exist. TASK-0711 removed them from the manifests.

## Problem Statement
- No Lit component exists for either tag in its owning service UI package.

## Documentation & Architecture Review
- AGENTS.md hard invariants and DoR 9 (no compatibility shims).
- ADR-0004, ADR-0013, ADR-0014.

## Product & User Story References
PRD-0024, PRD-0012, US-0076, US-0040

## Detailed Specification & Implementation Plan
1. Build `runefoble-bulletin-board` in `services/game_session/ui/src/` and `runefoble-campaign-telemetry` in `services/campaign_analytics/ui/src/`, against the existing routes.
2. Add Storybook stories, re-advertise both tags, and add Playwright BDD scenarios from US-0076 and US-0040.

## Frontdoor Blackbox Test Plan
- Vitest browser tests for both components.
- Playwright BDD scenarios from US-0076 and US-0040.

## Definition of Done
- The test plan passes.
- `make test`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: medium
- Source audits: TASK-0711 (Discovered)
