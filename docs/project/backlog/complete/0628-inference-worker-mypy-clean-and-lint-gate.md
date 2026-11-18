---
id: '0628'
title: Make mypy Pass on the Inference Worker and Add It to the Lint Gate
status: Complete
created: 2026-11-17
dependencies:
- TASK-0501
governing_adrs:
- ADR-0009
- ADR-0010
governing_prds:
- PRD-0001
governing_stories: []
target_release: 0.9.0
---

# TASK-0628: Make mypy Pass on the Inference Worker and Add It to the Lint Gate

## Status
Complete

## Summary
`uv run mypy services/inference_worker/src` reports 5 errors in 2 files. The `make lint` gate runs ruff only, so these errors never block a change. Fix the errors without ignores and add the mypy check for this service to the lint target.

## Problem Statement
- `services/inference_worker/src/inference_worker/llm_client.py:63,73`: `max_tokens` is rejected by the `ChatOpenAI` stub (`w2-inference-worker.md` F8). Verify at runtime first; the probe passed `max_tokens=512`, so the call may be right and the stub stale.
- `llm_client.py:65,75`: `api_key` typed `str` but the client expects `SecretStr` (pass `settings.openai_api_key`).
- `graphs/narration_graph.py:119`: `tension_level` typed `str` in state, model expects `Literal`.
- `make lint` (Makefile lint target) runs `ruff` only.

## Documentation & Architecture Review
- ADR-0009 (ruff and pre-commit): add mypy to the gate here; record the choice in the ADR text or a how-to note.
- ADR-0010 (CI): the lint gate is the CI gate.
- TASK-0501 (shim removal in the same package) touches `config.py` and `llm_client.py`; sequence after it. The shim claims in TASK-0501 are partly wrong (`w2-inference-worker.md` F14); correction in the index report.

## Product & User Story References
- PRD-0001 (Watcher inference path).

## Detailed Specification & Implementation Plan
1. Fix each of the 5 errors in place. No `# type: ignore` added.
2. Add `[tool.mypy]` settings for the package (strict for `services/inference_worker/src` only, or the defaults that already pass for the other packages).
3. Add a lint target line: `uv run mypy services/inference_worker/src`.
4. Confirm `uv run pytest tests/test_inference_worker.py` still passes.

## Frontdoor Blackbox Test Plan
- Before fix: `uv run mypy services/inference_worker/src` exits 1 with 5 errors.
- After fix: the same command exits 0; `make lint` runs it; the worker's `POST /inference/v1/intent` (through the public API) still returns a valid response with `SecretStr` configuration.

## Definition of Done
1. mypy passes for the worker with no ignores.
2. `make lint` includes the check and passes.
3. Existing worker tests pass.
4. No file above 500 lines.

## Audit Provenance

- Severity: medium
- Source audits: `w2-inference-worker.md`
