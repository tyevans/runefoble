---
id: '0912'
title: Services Type Their SpiceDB Callers With the Port, Not the Mock Union
status: Refined
created: 2026-11-19
dependencies:
- TASK-0911
governing_adrs:
- ADR-0001
- ADR-0015
governing_prds: []
governing_stories: []
target_bc: platform
target_release: 0.9.0
---
# TASK-0912: Services Type Their SpiceDB Callers With the Port, Not the Mock Union

## Status
Refined

## Summary
Eight service modules import `MockSpiceDBClient` and annotate their SpiceDB dependency as `SpiceDBClient | MockSpiceDBClient`. After TASK-0911 adds `SpiceDBPort`, these modules use the port and no longer import the mock package.

## Problem Statement
- `services/character_sheet/src/character_sheet/dependencies.py:20`, `:74`, `:231`.
- `services/character_sheet/src/character_sheet/roster.py:15`, `:22`.
- `services/character_sheet/src/character_sheet/authz.py:13`, `:16`.
- `services/game_session/src/game_session/contracts/auth.py:12`, `:16`.
- `services/game_session/src/game_session/campaign/tuples.py:15`, `:20`.
- `services/rules_compendium/src/rules_compendium/dependencies.py:7`, `:64`, `:73`.
- `services/rules_compendium/src/rules_compendium/homebrew_access.py:8`, `:32`, `:51`.
- `services/rules_compendium/src/rules_compendium/routers/encounters.py:8`, `:45`, `:108`.

## Documentation & Architecture Review
- ADR-0015 problem 4. TASK-0911 defines the port.
- ADR-0021: game_session files may move in TASK-0894 to TASK-0899. Edit the files where they are when this task starts.
- DoR 9: delete the local type aliases (`SpiceDB`, `Spicedb`, `AuthzClient`) or point them at the port. Do not keep both.

## Product & User Story References
None. Platform quality work.

## Detailed Specification & Implementation Plan
1. In each file above, replace the union with `SpiceDBPort` and remove the `runefoble_auth.mock` import.
2. Prefer one annotation per service (for example `SpiceDep = Annotated[SpiceDBPort, Depends(get_spicedb_client)]`) and reuse it.
3. Extend the TASK-0911 import test: importing each service `main` module does not load `runefoble_auth.mock`.

## Frontdoor Blackbox Test Plan
- One permission-gated HTTP route per service (character sheet read, game_session campaign grant, rules compendium homebrew write) returns the same status codes and bodies before and after.
- A fresh interpreter that imports `character_sheet.main`, `game_session.main` and `rules_compendium.main` has no `runefoble_auth.mock` in `sys.modules`.

## Definition of Done
- `grep -rn "runefoble_auth.mock" services/*/src` returns nothing.
- `uv run pytest`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: medium
- Source audits: `services-backend.md` (finding 1), `gateways-libs.md` (F1)
