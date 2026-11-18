---
id: '0771'
title: Gateway JSON Uses One Wire Casing
status: Refined
created: 2026-11-17
dependencies:
- TASK-0488
governing_adrs:
- ADR-0013
governing_prds: []
governing_stories: []
target_bc: gateway
target_release: 0.9.0
---

# TASK-0771: Gateway JSON Uses One Wire Casing

## Status
Refined. Round-3 triage (`.audit/drafts/round3-notes.md`).

## Summary
Gateway request models accept camelCase aliases beside snake_case field names. Two accepted spellings for one field is a compatibility shim.

## Problem Statement
- Gateway Pydantic request models declare camelCase aliases and also accept field names. The live frontend sends camelCase.

## Documentation & Architecture Review
- AGENTS.md hard invariants and DoR 9 (no compatibility shims).
- ADR-0013.

## Product & User Story References
None. Platform quality work.

## Detailed Specification & Implementation Plan
1. Decide one wire casing for the browser-facing gateway API and record it in `docs/reference/` (recommend camelCase on the wire through one shared alias generator; snake_case inside Python).
2. Apply it to every gateway request and response model through one base model. Refuse the other spelling.
3. Update the App Shell, microfrontends, e2e steps and tests to the chosen casing.

## Frontdoor Blackbox Test Plan
- POST with the chosen casing: accepted. POST with the other casing: 422.

## Definition of Done
- One wire casing on every gateway route, set in one base model.
- `uv run pytest`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: medium
- Source audits: `work/0488.md`
