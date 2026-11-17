---
id: '0607'
title: Inference Worker Explicit Backend Failure Contract and Response Provenance
status: Complete
created: 2026-11-17
dependencies: []
governing_adrs:
- ADR-0002
- ADR-0007
- ADR-0014
governing_prds:
- PRD-0001
- PRD-0002
governing_stories:
- US-0001
- US-0032
target_release: 0.9.0
severity: high
source_audits:
- w2-inference-worker.md
- w1-the-watcher.md
---

# TASK-0607: Inference Worker Explicit Backend Failure Contract and Response Provenance

## Status
Complete

## Summary
When the LLM backend fails, the worker returns `success: true` with canned text "[Generated response for prompt: ...]" and backend `mock`. The Watcher and players see a normal reply. This task makes backend failure an explicit error. Canned output is used only when the operator selects the `mock` backend. Every response reports its provenance (`llm`, `heuristic`, or `mock`).

## Problem Statement
- `services/inference_worker/src/inference_worker/llm_client.py:105-115`: on any exception the client logs a warning and returns `{"success": True, "content": "[Generated response for prompt: ...]", "backend": "mock"}`.
- `graphs/narration_graph.py:89-103` returns canned sensory details and prompts.
- The HTTP caller receives HTTP 200 with a normal body.
- `the_watcher/routers/intent/speech.py:54` uses `action.get("confidence", 0.9)` when the worker sends no confidence. `speech.py:56-57` falls back to a fixed template reply.
- The intent graph `mock` branch (`intent_graph.py` near lines 60-100) uses keyword rules. The response does not say so.

Sources: `.audit/reports/w2-inference-worker.md` F2; `.audit/reports/w1-the-watcher.md` F4 (worker part).

## Documentation & Architecture Review
- `docs/reference/` has no inference worker page yet. TASK-0607 adds one (see also worker port finding in w2-inference-worker F9). Keep it to the response schema for this task.
- `docs/how-to/configure-stand-in-guardrails-and-hot-swap.md`: check the expected fallback behaviour and update it.
- TASK-0448 (proposed, provider routing in The Watcher) is related but different. This task defines the response contract that TASK-0448 must follow.

## Product & User Story References
- `docs/project/product/accepted/prd-0001-the-watcher-ai-dm-and-board-animator.md`
- `docs/project/product/accepted/prd-0002-missing-player-ai-stand-in-with-penalties.md`
- `docs/project/user_stories/accepted/us-0032-custom-llm-provider-injection-and-intent-middleware.md`

## Detailed Specification & Implementation Plan
1. Add `source: Literal["llm", "heuristic", "mock"]` and `degraded: bool` to the worker response models in `models.py`.
2. `llm_client.py`: on backend failure with a real backend configured, raise a typed `InferenceBackendError`. The API maps it to HTTP 503 with `{"error": "backend_unavailable", "backend": <name>}`. Remove the canned string.
3. The `mock` backend returns `source: "mock"` and is selected only by explicit configuration.
4. Graph outputs set `source` from the path actually taken (LLM, regex heuristic, or mock).
5. Keep the tests on the mock backend as fixtures. Do not use the mock as a production fallback.

## Frontdoor Blackbox Test Plan
- Before fix: point the worker at an unreachable backend and POST an intent request. Response 200 with `success: true` and canned content (test fails).
- After fix: the same request returns 503 with `error: backend_unavailable`.
- After fix: with the mock backend configured, the response has `source: "mock"`.
- After fix: The Watcher speech route surfaces the 503 as its own error. It does not return a template reply.

## Definition of Done
1. The string "[Generated response for prompt" is not in production code.
2. Response models carry `source` and `degraded`. Files under 500 lines.
3. Blackbox tests pass. `uv run pytest services/inference_worker services/the_watcher` passes.
4. Ruff check and format pass.
5. Worker response schema documented under `docs/reference/`. `CHANGELOG.md` `[Unreleased]` entry added.
