---
id: '0740'
title: Inference Graphs Share One Failure Policy for Unusable Model Output
status: Refined
created: 2026-11-17
dependencies:
- TASK-0739
governing_adrs:
- ADR-0015
governing_prds:
- PRD-0001
governing_stories:
- US-0001
target_bc: inference_worker
target_release: 0.9.0
---
# TASK-0740: Inference Graphs Share One Failure Policy for Unusable Model Output

## Status
Refined. Found by the refactor audit round refactor-r1 and checked against the code on 2026-11-17.

## Summary
For the same bad model output, the intent graph returns a regex heuristic marked `degraded`, and the other two graphs raise an error. ADR-0015 decision 4 says no substitute output.

## Problem Statement
- `services/inference_worker/src/inference_worker/graphs/intent_graph.py:116-120`: a missing `action_type` returns `_heuristic_intent(...)` with `source: heuristic`, `degraded: True`.
- `graphs/stand_in_graph.py:105-107` and `narration_graph.py:103-104` raise `InferenceBackendError` for the same condition.
- Each graph checks `resp["source"] == "mock"` (`intent_graph.py:104`, `stand_in_graph.py:113`, `narration_graph.py:99`).
- `stand_in_graph.py` `generate_stand_in_decision_node` is 152 lines and holds mock-mode rules.

## Documentation & Architecture Review
- AGENTS.md hard invariants and DoR 9 (no compatibility shims).
- ADR-0015.
- `docs/reference/inference-worker-response-contract.md`: remove the `degraded` field if no path sets it. TASK-0691 covers the guardrail names in the mock rules: coordinate the move.

## Product & User Story References
- PRD-0001
- US-0001

## Detailed Specification & Implementation Plan
1. Add one `require_field(content, key)` output-contract function. Every graph raises `InferenceBackendError` when a required field is missing.
2. Remove the heuristic fallback and `degraded` from `intent_graph.py`. A degraded path, if product wants one, is an explicit port adapter (decide in a separate task).
3. Move the mock-mode rules from the stand-in graph into the mock adapter from TASK-0739. Check the mock source in one place.

Refactor round 2 addendum (2026-11-18): Also: remove `mock` from the production adapter registry (`services/inference_worker/src/inference_worker/llm_factory.py:32`). Refuse `RUNEFOBLE_WORKER_BACKEND=mock` at start-up in a deployed environment (`services/inference_worker/src/inference_worker/config.py:8` and `:33`; no validator covers it today). Cite ADR-0015 Context item 4, decision (b), and `docs/how-to/add-an-engine-port-adapter.md`. Do not cite ADR-0015 (f); that decision covers event stores.

## Frontdoor Blackbox Test Plan
- A stub LLM returns prose. `POST /inference/v1/intent` returns 503, not a heuristic action. Same for stand-in and narration routes.

## Definition of Done
- No graph sets `source: heuristic`. `generate_stand_in_decision_node` is under 60 lines.
- `uv run pytest`, `make lint`, and `make health-check` pass. No file over 500 lines.
- Docs touched by the change are correct. `CHANGELOG.md` has an `[Unreleased]` entry.

## Audit Provenance
- Severity: medium
- Source audits: `watcher-voice-inference.md (F8, F9 in part)`
