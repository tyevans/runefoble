---
id: '0914'
title: The Domain Error Handler Maps Only Domain Errors to 400
status: Refined
created: 2026-11-19
dependencies: []
governing_adrs:
- ADR-0015
- ADR-0011
governing_prds: []
governing_stories: []
target_bc: platform
target_release: 0.9.0
---
# TASK-0914: The Domain Error Handler Maps Only Domain Errors to 400

## Status
Refined

## Summary
`install_domain_error_handlers` maps every `ValueError` to 400 and sends the exception text to the client. A programming error that raises `ValueError`, or a `pydantic.ValidationError` raised inside service code, becomes a client error with internal text. Only refused domain commands may answer 400.

## Problem Statement
- `libs/runefoble_platform/src/runefoble_platform/domain_errors_http.py:23-24`: `_bad_request` returns `400` with `str(exc)`.
- `:35`: `app.add_exception_handler(ValueError, _bad_request)`.
- Users: `services/board_state/src/board_state/main.py` and `services/character_sheet/src/character_sheet/main.py`. `board_state` raises `ValueError` at 6 sites in 4 files. `character_sheet` raises it at 7 sites in 5 files.
- `services/board_state/src/board_state/errors.py:9` and `encounter_consumer.py:41` subclass `ValueError` for domain refusals.

## Documentation & Architecture Review
- ADR-0015 problem 4 (failures look like success or like client error). TASK-0752 (complete) created this mapping.
- Hard Invariant 2: refusals come from aggregates and domain modules.
- DoR 9: no handler that still catches plain `ValueError`.

## Product & User Story References
None. Platform quality work.

## Detailed Specification & Implementation Plan
1. Add `DomainRefusedError` (400) and `DomainNotFoundError` (404) in `libs/runefoble_platform`. Map only these and `AggregateNotFoundError`.
2. In `board_state` and `character_sheet`, change each refusal `raise ValueError` to the domain error (or a subclass). Change `BoardElementNotFoundError` and `EncounterPlacementError` to subclass the new bases.
3. Leave other `ValueError` values unmapped. They reach the platform 500 handler with a fixed detail and no exception text.
4. Update the module docstring and the reference page that describes domain error mapping (find it with `grep -rn domain_errors docs/`).

## Frontdoor Blackbox Test Plan
- Every existing 400 and 404 route test in `board_state` and `character_sheet` passes unchanged.
- One new test per service: a request that reaches an internal `ValueError` (for example, a malformed stored value read through a public route, set up through public routes only) answers 500 with the fixed detail. If no such path exists through the frontdoor, test the handler on a small FastAPI app that installs `install_domain_error_handlers` and has one route that raises `ValueError`.

## Definition of Done
- `install_domain_error_handlers` does not register `ValueError`.
- Docs updated. `uv run pytest`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: medium
- Source audits: `gateways-libs.md` (F5)
