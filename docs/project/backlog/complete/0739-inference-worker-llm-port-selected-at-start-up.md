---
id: '0739'
title: Inference Worker Uses an LLM Port Selected at Start-Up
status: Complete
created: 2026-11-17
dependencies: []
governing_adrs:
- ADR-0015
governing_prds:
- PRD-0001
governing_stories:
- US-0001
target_bc: inference_worker
target_release: 0.9.0
---
# TASK-0739: Inference Worker Uses an LLM Port Selected at Start-Up

## Status
Complete

## Summary
Backend selection, probing, model factory, and calls are one class. The backend probe runs on every request, every error becomes a backend error, and the graphs type-hint the concrete class.

## Problem Statement
- `services/inference_worker/src/inference_worker/llm_client.py:45-138`: `MultiBackendLLMClient` probes endpoints (`:52-81`), builds `ChatOpenAI` in an if-chain (`:83-103`), and invokes the model (`:109-138`).
- `llm_client.py:115`: `generate_completion` calls `detect_available_backend()` on every request.
- `llm_client.py:129-131`: `except Exception` converts every error into `InferenceBackendError`.
- Backend names repeat in `config.py:29`, `main.py:17`, and the if-chain. The graphs `graphs/intent_graph.py:82`, `stand_in_graph.py:50`, `narration_graph.py:74` type-hint the concrete class. `api.py:25-26` builds the client at import time.

## Documentation & Architecture Review
- AGENTS.md hard invariants and DoR 9 (no compatibility shims).
- ADR-0015.
- `docs/how-to/add-an-engine-port-adapter.md`, `docs/reference/inference-worker-response-contract.md`, `docs/reference/embedding-providers.md` (pattern).
- Check `deployments/helm` and `.env.worker` for `RUNEFOBLE_WORKER_BACKEND=auto` before the change. A bad value now stops start-up.

## Product & User Story References
- PRD-0001
- US-0001

## Detailed Specification & Implementation Plan
1. Add `inference_worker/ports.py`: `LLMPort` with `async complete(system_prompt, user_prompt) -> Completion` (typed dataclass: `content`, `backend`, `source`).
2. Add adapters `openai_compatible.py`, `ollama.py`, and `mock.py` (mock is selected only by an explicit setting). Each raises `EngineUnavailableError` from `runefoble_platform.engine_ports` on failure.
3. Add `build_llm_port(settings)` using `build_adapter`, called from the app lifespan. An unknown or unreachable backend stops start-up. Remove per-request probing. Resolve `auto` once in the lifespan, or remove it.
4. Graphs receive `LLMPort`. Build the graph set once in the lifespan.
5. Map `EngineUnavailableError` to 503 with the existing body keys (`backend_unavailable`, `backend`).

## Frontdoor Blackbox Test Plan
- Existing `tests/test_inference_worker_failure_contract.py` stays green.
- `POST /inference/v1/intent` with a stub `LLMPort` that raises returns 503 with `error: backend_unavailable`.
- A bad backend value fails start-up and names the allowed values.

## Definition of Done
- No request-path code probes backends. `grep` finds no `MultiBackendLLMClient` type hint in graphs.
- `uv run pytest`, `make lint`, and `make health-check` pass. No file over 500 lines.
- Docs touched by the change are correct. `CHANGELOG.md` has an `[Unreleased]` entry.

## Audit Provenance
- Severity: high
- Source audits: `watcher-voice-inference.md (F1)`
