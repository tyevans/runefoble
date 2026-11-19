---
id: '0919'
title: Audience Narration Uses the Narrator Port, Not the Engine Name
status: Refined
created: 2026-11-19
dependencies: []
governing_adrs:
- ADR-0015
governing_prds:
- PRD-0001
governing_stories:
- US-0031
target_bc: the_watcher
target_release: 0.9.0
---
# TASK-0919: Audience Narration Uses the Narrator Port, Not the Engine Name

## Status
Refined

## Summary
`audience_narration.py` reads the engine settings on each call, checks the engine name for `"heuristic"`, and calls the inference worker over HTTP itself. The engine selection module already builds a `SceneNarrator` port for each engine. The heuristic narrator already raises `EngineUnavailableError`. The narration code duplicates the selection and the worker call.

## Problem Statement
- `services/the_watcher/src/the_watcher/audience_narration.py:82-84`: `settings = WatcherEngineSettings()` per call, then `if settings.watcher_engine == "heuristic"`.
- `:85-98`: a direct `call_worker(settings.inference_url, WORKER_PATH, ...)` beside the port.
- `services/the_watcher/src/the_watcher/engine_selection.py:51-56`: `WatcherPorts.narrator` is the selected `SceneNarrator`. `:99`: the heuristic choice maps to `HeuristicSceneNarrator`.
- `services/the_watcher/src/the_watcher/adapters/heuristic_engines.py:55-60`: the heuristic narrator raises `EngineUnavailableError`.

## Documentation & Architecture Review
- ADR-0015 problem 4. `docs/how-to/add-an-engine-port-adapter.md`: engine names are read only in the selection module.
- `docs/how-to/orchestrate-audience-chaos-polls.md`: the whisper text for an unavailable engine stays.
- Whether the heuristic engine stays in deployed environments is a separate product decision. This task does not decide it.

## Product & User Story References
- PRD-0001 (The Watcher). US-0031 (audience chaos polls).

## Detailed Specification & Implementation Plan
1. Give `record_audience_narration` the `WatcherPorts` (from the app container, or from `load_watcher_ports` until TASK-0916 lands).
2. Build a `DMGuidanceRequest` from the modifier and call `ports.narrator.narrate`. Map `EngineUnavailableError` to the existing unavailable whisper.
3. Remove the engine name check, the per-call settings read and the direct worker call. If the worker payload for audience modifiers differs from `DMGuidanceRequest`, add the needed field to the port request, not a second path.

## Frontdoor Blackbox Test Plan
- Publish an approved audience modifier event (standard domain event). With the worker up (live loopback), the DM whisper read shows narration text.
- With `RUNEFOBLE_WATCHER_ENGINE=heuristic`, and with the worker down, the whisper read shows the unavailable notice.

## Definition of Done
- `grep -n "watcher_engine ==" services/the_watcher/src` finds only `engine_selection.py`.
- `uv run pytest`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: low
- Source audits: `services-backend.md` (finding 5)
