---
id: '0943'
title: The Watcher Selects Each Engine Port by Its Own Setting, and Grammar Runs First
status: Complete
created: 2026-11-19
dependencies:
- '0942'
governing_adrs:
- ADR-0015
- ADR-0022
governing_prds:
- prd-0025-voice-first-release-one
governing_stories:
- us-0001-player-commands-board-via-voice
target_bc: the_watcher
target_release: 1.0.0
---

# TASK-0943: The Watcher Selects Each Engine Port by Its Own Setting, and Grammar Runs First

## Status

Complete

## Summary

One switch, `RUNEFOBLE_WATCHER_ENGINE`, selects the intent parser, the stand-in engine and the narration engine together. In Kind it selects the inference worker. Every spoken transcript therefore needs the language model, even a plain move. This task replaces the switch with one setting for each port. The intent port parses with the grammar first. Only a transcript that the grammar returns as `narrative` goes to the worker. A worker failure returns 503.

## Problem Statement

- `services/the_watcher/src/the_watcher/engine_selection.py:29-38`: one `WatcherEngineName` for all ports. The default is `inference_worker`.
- `services/the_watcher/src/the_watcher/engine_selection.py:70-109`: `build_watcher_ports` builds the intent, stand-in and narrator ports from the one value.
- `deployments/helm/runefoble/values.yaml:316`: `RUNEFOBLE_WATCHER_ENGINE: inference_worker`.
- `services/the_watcher/src/the_watcher/routers/intent/speech.py:36`: the speech route calls the worker-backed intent port for every transcript.
- `services/the_watcher/src/the_watcher/routers/intent/compound.py:59`: the compound route calls the grammar only, with no rule. ADR-0022 (a) and (b) give the rule.
- `services/the_watcher/src/the_watcher/adapters/heuristic_engines.py` (removed): the heuristic stand-in decider returns template text. ADR-0015 Context item 4 forbids this kind of output. `heuristic_engines.py:55-60`: the heuristic narrator raises 503 and has no text.
- Docs that name the setting: `docs/reference/platform-services.md`, `docs/how-to/add-an-engine-port-adapter.md`, `docs/how-to/compose-a-service-with-an-app-container.md`, `docs/how-to/test-cross-service-calls-with-live-upstreams.md`, `docs/reference/inference-worker-response-contract.md`.
- Tests that set the switch: `tests/helpers/watcher_engine.py:9-13`, `tests/test_blackbox_watcher_engine_ports.py`.

## Documentation & Architecture Review

- ADR-0022 (a) to (e). Decision (d) names the new settings and removes the old name with no alias.
- ADR-0015 Context item 4 (fallbacks hide failures) and decision (e) (service credential).
- `docs/how-to/add-an-engine-port-adapter.md`: update the port list, the setting names and the 503 rule.
- `docs/reference/inference-worker-response-contract.md`: update the setting name only.

## Product & User Story References

- PRD-0025: "Speech does nothing for the game", and checkable outcome 2.
- US-0001.

## Detailed Specification & Implementation Plan

1. Replace `RUNEFOBLE_WATCHER_ENGINE` with three settings, read through `WatcherEngineSettings`:
   - `RUNEFOBLE_WATCHER_INTENT_ENGINE`: the intent fallthrough.
   - `RUNEFOBLE_WATCHER_STAND_IN_ENGINE`.
   - `RUNEFOBLE_WATCHER_NARRATION_ENGINE`.
   Each accepts `inference_worker` or `none`. The default is `none`. Remove the old name and the value `heuristic` from every reader. Do not add an alias.
2. Intent port, in this order, for each transcript:
   a. Parse with the grammar (`TheWatcherEngine.parse_speech_intent`).
   b. If the result is `move`, `attack`, `skill_check` or `roll_dice`, return it. Its `source` is `watcher_rules`.
   c. If the result is `narrative`, and the intent setting is `inference_worker`, call the worker. Its `source` is `llm`.
   d. If the result is `narrative`, and the intent setting is `none`, return `action_type` `narrative` with the watcher reply "Not understood." It never invents an action.
   e. If the worker call fails or times out, return 503. Do not parse again with the grammar. Do not try another engine.
   f. If the grammar raises an error, return that error. Do not call the worker.
3. Compound route (`compound.py:59`): the single-intent result comes from the same intent port. The multi-node parse (`nodes`) stays on the grammar. State this in the module docstring. A node never reaches the worker.
4. Stand-in and narration ports: the `inference_worker` value builds the worker adapter. The `none` value raises `EngineUnavailableError`, which maps to 503 as it does today.
5. Delete `heuristic_engines.py`. The grammar stays in `TheWatcherEngine`. The stand-in and narration templates are removed.
6. Update `values.yaml` at line 316 to set the three new settings. Set the intent and stand-in and narration values to `inference_worker`. This keeps the current Kind behaviour for stand-ins and narration.
7. Update the tests and the docs named above.

## Frontdoor Blackbox Test Plan

Tests use the public gateway route `POST /api/v1/watcher/speak-and-act` and the public compound route. Use live loopback upstreams. Select the port values through the environment, as `tests/helpers/watcher_engine.py` does.

- Intent `none`, transcript "move 2 squares west": a `move` result with `source` `watcher_rules`. The worker is never called.
- Intent `inference_worker`, transcript "move 2 squares west": a `move` result. The worker is never called, because the grammar parses it.
- Intent `inference_worker`, a transcript the grammar returns as `narrative`, worker live: `source` `llm`.
- Intent `inference_worker`, the worker down or slow: 503. The grammar does not run a second time.
- Intent `none`, a `narrative` transcript: "Not understood." and no worker call.
- Stand-in `none`: the stand-in route returns 503. Narration `none`: the narration route returns 503.
- Each old setting name, if set, has no effect. The test sets `RUNEFOBLE_WATCHER_ENGINE=inference_worker` and checks that the setting is not read.
- The compound route single intent: grammar only for `move` and `skill_check`. A `narrative` single intent follows the intent port rule.

## Definition of Done

- Every test in the plan passes, with `uv run pytest` on the named files.
- `grep -rn RUNEFOBLE_WATCHER_ENGINE` in `services deployments docs tests gateway libs e2e` returns no match, except in `CHANGELOG.md` and completed backlog records.
- `heuristic_engines.py` is deleted. No file imports it.
- `values.yaml` sets the three new settings.
- Every doc named in "Problem Statement" is updated.
- A CHANGELOG `Changed` entry under `[Unreleased]` says that the engine settings changed and that the old name is removed.
- Every file the task touches stays under 500 lines.

## Audit Provenance

- Severity: high (PRD-0025 release blocker).
- Source audits: `.audit/research/r1-watcher-llm.md` ("RUNEFOBLE_WATCHER_ENGINE switches all three ports together"), `.audit/research/r1-voice-path.md` (section 1, step 7).
