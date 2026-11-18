---
id: '0741'
title: The Watcher Selects Its Intent, Stand-In, and Narration Engines Through Ports
status: Refined
created: 2026-11-17
dependencies: []
governing_adrs:
- ADR-0015
governing_prds:
- PRD-0001
- PRD-0002
governing_stories:
- US-0001
- US-0002
target_bc: the_watcher
target_release: 0.9.0
---
# TASK-0741: The Watcher Selects Its Intent, Stand-In, and Narration Engines Through Ports

## Status
Refined. Found by the refactor audit round refactor-r1 and checked against the code on 2026-11-17.

## Summary
Three routers choose between the inference worker and a local regex or template engine with `if INFERENCE_URL`. An unset URL silently serves heuristic output. ADR-0015 decision 4 forbids substitute output.

## Problem Statement
- `services/the_watcher/src/the_watcher/routers/intent/speech.py:69-72`: `if INFERENCE_URL:` calls the worker, then `if intent is None:` calls `engine.parse_speech_intent`.
- `routers/stand_in.py:36-37` repeats the branch for stand-in actions. `routers/autonomous_dm.py:82-83` logs an error when the URL is unset and continues.
- `main.py:84` reports "using local heuristic engine". `dependencies.py:29` reads the URL at import time.
- `movement_parser.py:78-192`: the local engine is a 115-line regex if-chain.

## Documentation & Architecture Review
- AGENTS.md hard invariants and DoR 9 (no compatibility shims).
- ADR-0015.
- `docs/how-to/add-an-engine-port-adapter.md` (the pattern from voice_agent), `docs/explanation/the-watcher-autonomous-dm.md`.
- TASK-0691 covers guardrail names in the local engine. TASK-0448 adds providers. Neither removes the selection branches.

## Product & User Story References
- PRD-0001
- PRD-0002
- US-0001
- US-0002

## Detailed Specification & Implementation Plan
1. Add `the_watcher/ports.py`: `IntentParser`, `StandInDecider`, `SceneNarrator`.
2. Adapters: `inference_worker` (uses `worker_client.call_worker`) and `local_heuristic` (wraps the current engine).
3. Select each with `build_adapter` in the lifespan from a setting `RUNEFOBLE_WATCHER_ENGINE=inference_worker|heuristic`. No default hides a missing URL: the `inference_worker` adapter fails start-up when the URL is unset. Set the value in Helm.
4. Routers call the port only. Remove the `if` branches and the dead `None` check. Tests that need heuristics set the explicit setting.

## Frontdoor Blackbox Test Plan
- `POST /api/v1/watcher/transcribe-and-act` with the worker stopped returns 503 and publishes no `SpeechIntentParsed` event.
- Start-up with `inference_worker` selected and no URL fails with a clear error.
- Existing `tests/test_blackbox_watcher_no_placeholders.py` and `tests/test_blackbox_stand_in_guardrail_contract.py` pass with the explicit setting.

## Definition of Done
- No router reads `INFERENCE_URL`. Helm sets the engine setting.
- `uv run pytest`, `make lint`, and `make health-check` pass. No file over 500 lines.
- Docs touched by the change are correct. `CHANGELOG.md` has an `[Unreleased]` entry.

## Audit Provenance
- Severity: high
- Source audits: `watcher-voice-inference.md (F2)`
