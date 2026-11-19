---
id: '0841'
title: Test Setup Writes No SpiceDB Tuples Outside the SpiceDB Sync Tests
status: Proposed
created: 2026-11-18
dependencies:
- TASK-0716
governing_adrs:
- ADR-0001
- ADR-0014
governing_prds:
- PRD-0023
governing_stories:
- US-0063
target_release: 0.9.0
---

# TASK-0841: Test Setup Writes No SpiceDB Tuples Outside the SpiceDB Sync Tests

## Status
Proposed

## Summary
After TASK-0716, 132 Python test files (106 under `tests/`) still call `write_relationship` to set up permissions. Hard Invariant 7 asks for setup through public frontdoors. Split the work into waves by bounded context. Each wave replaces tuple seeding with the public campaign, invite and join routes (`tests/helpers/campaign_setup.py`) or with the owner's create routes, which write their own tuples.

## Open Questions
1. Which tuples have no public route that writes them (for example spectator grants or character ownership in another campaign)? Those need a route first or an explicit exception list.
2. Group the 132 files into waves of at most 15 files each.

## Product & User Story References
- [`prd-0023-unified-frontend-application-shell-and-campaign-hub.md`](../../product/accepted/prd-0023-unified-frontend-application-shell-and-campaign-hub.md)
