---
id: '0720'
title: SpiceDB Settings Are Split From PlatformSettings
status: Complete
created: 2026-11-17
dependencies:
- TASK-0541
governing_adrs:
- ADR-0001
- ADR-0015
governing_prds: []
governing_stories: []
target_bc: core
target_release: 0.9.0
---
# TASK-0720: SpiceDB Settings Are Split From PlatformSettings

## Status
Complete

## Summary
`PlatformSettings` holds about 60 fields. It requires the SpiceDB key in every service that imports it, including services that never call SpiceDB. SpiceDB config is read twice. This first slice extracts SpiceDB settings only.

## Problem Statement
- `libs/runefoble_platform/src/runefoble_platform/config.py:15-235`: about 60 fields. `:134` declares `spicedb_preshared_key: str` with no default. `PlatformSettings(_env_file=None)` without the key raises `ValidationError`.
- Modules that build it at import but never use SpiceDB: `services/voice_agent/src/voice_agent/dependencies.py:24`, `services/voice_agent/src/voice_agent/event_bus.py:8`, `gateway/mcp/src/gateway_mcp/asgi.py:10`. Twenty-nine non-test modules build it.
- `libs/runefoble_auth/src/runefoble_auth/spicedb.py:27-28` reads the same names with `os.getenv` at import.

## Documentation & Architecture Review
- AGENTS.md hard invariants and DoR 9 (no compatibility shims).
- ADR-0001, ADR-0015.
- `docs/how-to/` and `docs/reference/` pages named in the specification.

## Product & User Story References
None. Platform quality work.

## Detailed Specification & Implementation Plan
1. Add `SpiceDBSettings` (endpoint, preshared key, no default for the key) in `runefoble_auth`. `spicedb.py` reads it, not `os.getenv`.
2. Remove the SpiceDB fields from `PlatformSettings`. Services that call SpiceDB build `SpiceDBSettings`. Others do not need the key.
3. Keep every environment variable name through `AliasChoices`.
4. Align with the factory in TASK-0541: it takes `SpiceDBSettings`.
5. File follow-ups for the other concerns (storage, telemetry, mail, gateway upstream URLs, four BC settings classes at `config.py:237-329`). Do not do them here.

## Frontdoor Blackbox Test Plan
- Start voice_agent with `RUNEFOBLE_SPICEDB_PRESHARED_KEY` unset. `GET /healthz` returns 200.
- Start a service that checks permissions with the key unset. It fails at start-up with `ConfigurationError`.
- `helm template` and `helm lint` pass.

## Definition of Done
- The specification steps are done and the tests above pass.
- Docs named in the specification are corrected.
- `uv run pytest`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: medium
- Source audits: `refactor-r1/libs.md`
