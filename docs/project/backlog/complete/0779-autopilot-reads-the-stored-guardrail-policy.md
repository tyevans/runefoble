---
id: '0779'
title: Autopilot Reads the Stored Guardrail Policy
status: Complete
created: 2026-11-17
dependencies:
- TASK-0691
governing_adrs:
- ADR-0015
- ADR-0011
governing_prds: []
governing_stories: []
target_bc: the_watcher
target_release: 0.9.0
---

# TASK-0779: Autopilot Reads the Stored Guardrail Policy

## Status
Complete

## Summary
Autopilot takes the stand-in guardrail policy from its request body. The caller can send a weaker policy than the one stored on the character, so the DM-set guardrails do not bind the stand-in.

## Problem Statement
- TASK-0691 typed and enforced the policy, but autopilot still reads it from the request (`.audit/work/0691.md`, Gap).
- `services/character_sheet/src/character_sheet/models/base.py:45-46` stores `avoid_melee=True` and `permadeath_safeguard=True` as defaults. The shared model defaults `avoid_melee=False`. The two defaults differ.
- `services/game_session/src/game_session/routers/autopilot.py:15` and `models/session.py:9` import `the_watcher` in process (ADR-0015 c and e).

## Documentation & Architecture Review
- AGENTS.md hard invariants and DoR 9 (no compatibility shims).
- ADR-0015, ADR-0011.
- `docs/how-to/configure-stand-in-guardrails-and-hot-swap.md`.

## Product & User Story References
None. Platform quality work.

## Detailed Specification & Implementation Plan
1. Autopilot loads the guardrail policy of the stand-in character from character_sheet through the shared `ServiceClient`. The request body carries no policy.
2. One default policy, defined once in the shared contract. Remove the second set of defaults.
3. Replace the in-process `the_watcher` import in game_session with an HTTP call or a shared contract in `libs/`.

## Frontdoor Blackbox Test Plan
- Store a strict policy through the character_sheet route, then run autopilot with a request that has no policy: the stand-in obeys the stored policy.
- A request body that carries a policy answers 422.

## Definition of Done
- The stored character policy is the only policy autopilot uses.
- `uv run pytest`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: high
- Source audits: `.audit/work/0691.md` (Gap, Discovered)
