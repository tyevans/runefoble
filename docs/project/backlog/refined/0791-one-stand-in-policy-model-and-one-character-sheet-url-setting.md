---
id: '0791'
title: One Stand-In Policy Model and One Character Sheet URL Setting
status: Refined
created: 2026-11-17
dependencies: []
governing_adrs:
- ADR-0015
governing_prds: []
governing_stories: []
target_bc: gateway_api
target_release: 0.9.0
---

# TASK-0791: One Stand-In Policy Model and One Character Sheet URL Setting

## Status
Refined. Found during batch 23 integration, 2026-11-17.

## Summary
The gateway keeps a second stand-in policy model with camelCase aliases and an unvalidated `risk_threshold`. game_session and the gateway read the character sheet URL from two different environment names.

## Problem Statement
- `gateway/api/src/gateway_api/character_models.py:109`: `StandInGuardrailsRequest`.
- `services/game_session/src/game_session/character_client.py`: `RUNEFOBLE_CHARACTER_SHEET_URL`. The gateway reads `CHARACTER_SHEET_URL`.

## Documentation & Architecture Review
- AGENTS.md hard invariants and DoR 9 (no compatibility shims).
- ADR-0015.

## Product & User Story References
None. Platform quality work.

## Detailed Specification & Implementation Plan
1. The gateway forwards the policy body raw and character_sheet validates it. Delete the gateway model.
2. Use one setting name through `PlatformSettings` in both processes. Update Helm values and docs.

## Frontdoor Blackbox Test Plan
- An invalid `risk_threshold` through the gateway answers 422 from the owner.
- Helm template renders one character sheet URL name.

## Definition of Done
- The test plan passes.
- `uv run pytest`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: low
- Source audits: `.audit/work/0779.md` (Discovered)
