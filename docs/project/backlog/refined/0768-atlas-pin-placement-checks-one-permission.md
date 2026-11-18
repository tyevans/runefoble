---
id: '0768'
title: Atlas Pin Placement Checks One Permission in Gateway and Service
status: Refined
created: 2026-11-17
dependencies:
- TASK-0695
governing_adrs:
- ADR-0001
governing_prds: []
governing_stories: []
target_bc: campaign_lore
target_release: 0.9.0
---

# TASK-0768: Atlas Pin Placement Checks One Permission in Gateway and Service

## Status
Refined. Found during the authz-int integration (`.audit/work/authz-int.md`, Discovered).

## Summary
The gateway atlas pin POST requires `run_session`. campaign_lore requires `play`. A player that the
service allows is refused at the gateway. The schema already defines the right check:
`atlas.place_pin = campaign->play + campaign->run_session`.

## Problem Statement
- Gateway lore write route for atlas pins (TASK-0695) checks `run_session`.
- campaign_lore `routers/atlas.py` checks `play`.

## Documentation & Architecture Review
- ADR-0001 and `libs/runefoble_auth/schema/runefoble.zed` (`definition atlas`).

## Product & User Story References
None. Authorization consistency.

## Detailed Specification & Implementation Plan
1. campaign_lore checks `atlas.place_pin` on pin create.
2. The gateway does not repeat a different check. It forwards the bearer, and the owning service
   decides (thin gateway). If the gateway keeps a check, it uses `atlas.place_pin`.
3. Update the atlas pin Gherkin journey if its setup grants the wrong relation.

## Frontdoor Blackbox Test Plan
- A player (`campaign#player`) places a pin through the gateway: 201, and the pin is in the atlas read.
- A viewer only: 403 from the gateway route, no pin written.

## Definition of Done
- Gateway and service agree on `atlas.place_pin`.
- `uv run pytest`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: medium
- Source audits: `work/authz-int.md`
