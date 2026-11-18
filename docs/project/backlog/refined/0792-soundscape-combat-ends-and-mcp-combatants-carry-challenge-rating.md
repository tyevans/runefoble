---
id: '0792'
title: Soundscape Leaves Combat When an Encounter Ends and MCP Combatants Carry Challenge Rating
status: Refined
created: 2026-11-17
dependencies: []
governing_adrs:
- ADR-0011
governing_prds: []
governing_stories: []
target_bc: soundscape
target_release: 0.9.0
---

# TASK-0792: Soundscape Leaves Combat When an Encounter Ends and MCP Combatants Carry Challenge Rating

## Status
Refined. Found during batch 23 integration, 2026-11-17.

## Summary
Soundscape never handles the encounter end event, so combat stays active and later health changes still score as combat. The MCP gateway starts combatants with no challenge rating, so the new tension input from TASK-0618 is always zero in production.

## Problem Statement
- `services/soundscape/src/soundscape/event_handlers.py`: no subscription for `CombatEncounterEnded`.
- `gateway/mcp/src/gateway_mcp/tools/board.py:132`: combatants start without `cr`.

## Documentation & Architecture Review
- AGENTS.md hard invariants and DoR 9 (no compatibility shims).
- ADR-0011.

## Product & User Story References
None. Platform quality work.

## Detailed Specification & Implementation Plan
1. Subscribe to `CombatEncounterEnded`. Clear combat state and re-score tension once.
2. The MCP encounter tool sends each combatant challenge rating from the rules compendium or the request. A missing rating is a validation error, not zero.

## Frontdoor Blackbox Test Plan
- Publish encounter start, then end, then a health change: the last tension score is a non-combat score.
- An MCP encounter start with rated combatants gives a non-zero enemy balance in the soundscape read model.

## Definition of Done
- The test plan passes.
- `uv run pytest`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: medium
- Source audits: `.audit/work/0618.md` (Discovered)
