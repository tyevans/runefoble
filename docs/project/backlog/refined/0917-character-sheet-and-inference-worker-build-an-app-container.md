---
id: '0917'
title: Character Sheet and the Inference Worker Build Their Dependencies in an App Container
status: Refined
created: 2026-11-19
dependencies: []
governing_adrs:
- ADR-0021
- ADR-0011
- ADR-0015
governing_prds: []
governing_stories: []
target_bc: character_sheet
target_release: 0.9.0
---
# TASK-0917: Character Sheet and the Inference Worker Build Their Dependencies in an App Container

## Status
Refined

## Summary
`character_sheet` reads settings and builds its repositories at import time. The inference worker keeps its LLM port and three graphs in module globals that `set_llm_port` writes. Neither service is in TASK-0755 or TASK-0859.

## Problem Statement
- `services/character_sheet/src/character_sheet/dependencies.py:46`: `platform_settings = PlatformSettings()` at import. `:48`: `load_spicedb_settings()` at import, result dropped. `:65-67`: module-level event bus provider with a `set_` seam. Module-level repositories follow.
- `services/inference_worker/src/inference_worker/api.py:27-31`: import-time `settings` and `llm_port`, `intent_graph`, `narration_graph`, `stand_in_graph` globals. `:34-40`: `set_llm_port` writes them with `global`.

## Documentation & Architecture Review
- TASK-0755 (complete) and `docs/how-to/compose-a-service-with-an-app-container.md`: the container pattern. TASK-0859 (refined): the same pattern for four services.
- `docs/reference/inference-worker-response-contract.md`: the contract does not change.
- TASK-0912 changes the SpiceDB annotations in `character_sheet/dependencies.py`. Coordinate edits.
- DoR 9: remove the seams. Tests build a container.

## Product & User Story References
None. Platform quality work.

## Detailed Specification & Implementation Plan
1. `character_sheet`: add `container.py`. Build settings, the SpiceDB client, the event bus and the repositories in the lifespan. Store on `app.state`. Change the `Depends` providers to read it. Remove the module globals and seams.
2. `inference_worker`: add a container that holds the settings, the selected `LLMPort` and the three graphs. The lifespan builds it once. Routes read it through `Depends`. Remove `set_llm_port` and the globals.
3. Update test fixtures in both services to pass a container.

## Frontdoor Blackbox Test Plan
- All existing character sheet and inference worker route tests pass with container fixtures.
- Start each app in a subprocess without a required setting. Assert that the lifespan fails with the setting name.
- Inference worker: a live loopback model endpoint answers an intent parse through `POST` on the public route, as today.

## Definition of Done
- No `global` statement and no import-time settings read in the two modules.
- `uv run pytest`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: medium
- Source audits: `services-backend.md` (finding 2)
