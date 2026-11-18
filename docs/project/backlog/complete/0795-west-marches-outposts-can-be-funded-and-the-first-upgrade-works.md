---
id: '0795'
title: West Marches Outposts Can Be Funded and the First Upgrade Works
status: Complete
created: 2026-11-17
dependencies: []
governing_adrs:
- ADR-0011
- ADR-0001
governing_prds: []
governing_stories: []
target_bc: campaign_lore
target_release: 0.9.0
---

# TASK-0795: West Marches Outposts Can Be Funded and the First Upgrade Works

## Status
Complete

## Summary
An outpost upgrade in a frontier with no outposts raises `KeyError`, because the default outpost id is not in the map. Outposts have no funding route, so their stored resources only drain.

## Problem Statement
- `services/campaign_lore/src/campaign_lore/west_marches_aggregate.py`: `upgrade_outpost`, empty outposts branch.
- No route adds resources to an outpost.

## Documentation & Architecture Review
- AGENTS.md hard invariants and DoR 9 (no compatibility shims).
- ADR-0011, ADR-0001.

## Product & User Story References
None. Platform quality work.

## Detailed Specification & Implementation Plan
1. Create the default outpost under the id that the lookup uses, or answer 404 for an unknown outpost.
2. Add a contribution command that moves gold from a campaign stronghold treasury into the outpost store. The contributor needs `stronghold.manage` on the source and play on the frontier. If the debit crosses services, call game_session through its public route with the service credential.

## Frontdoor Blackbox Test Plan
- A first upgrade in an empty frontier answers 200 or 404, never 500.
- A contribution debits the stronghold, credits the outpost, and a shortfall answers 409 with no events.

## Definition of Done
- The test plan passes.
- `uv run pytest`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: medium
- Source audits: `.audit/work/0786.md` (Discovered)
