---
id: '0501'
title: Remove Backward Compatibility Shims & Re-exports in inference_worker
status: Refined
created: 2026-09-29
dependencies:
- TASK-0002
- TASK-0448
governing_adrs:
- ADR-0003
- ADR-0007
- ADR-0008
governing_prds:
- PRD-0003
governing_stories:
- US-0002
- US-0010
target_release: 0.9.0
---

# TASK-0501: Remove Backward Compatibility Shims & Re-exports in inference_worker

## Status
Refined

## Summary
Excise legacy fallback backend configurations, deprecated message payload bridges, and transitional re-export facades from `services/inference_worker`, standardizing on canonical LLM backend configuration and LangGraph execution pipelines.

## Problem Statement
In `services/inference_worker`:
- `src/inference_worker/config.py` and `llm_client.py` contain legacy backend probing fallbacks and compatibility parameter mappings designed for transitional LLM server configurations.
- Transitional consumer message formats were retained in `redis_consumer.py` to support early schema versions.
Under the updated DoR, these transitional compatibility branches must be excised to ensure the inference worker maintains a lean, authoritative execution architecture without carrying obsolete compatibility code.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/explanation/the-watcher-autonomous-dm.md`: Autonomous inference worker architecture.
  - `docs/reference/platform-services.md`: Inference worker ports and environment variables.
- **Governing Architecture & ADRs**:
  - **ADR-0003: UV Monorepo Workspace**: Microservice boundaries.
  - **ADR-0007: Speech-to-Intent Pipeline**: Intent inference execution.
  - **ADR-0008: FastMCP Gateway**: Tool invocation and LLM interaction.

## Product & User Story References
- [`prd-0003-the-watcher-autonomous-dm-engine.md`](../../product/accepted/prd-0003-the-watcher-autonomous-dm-engine.md)
- [`us-0002-autonomous-dm-intent-arbitration.md`](../../user_stories/accepted/us-0002-autonomous-dm-intent-arbitration.md)
- [`us-0010-developer-local-infrastructure-and-test-tooling.md`](../../user_stories/accepted/us-0010-developer-local-infrastructure-and-test-tooling.md)

## Detailed Specification & Implementation Plan
1. **Remove Legacy Backend Configuration Shims**:
   - In `services/inference_worker/src/inference_worker/config.py` and `llm_client.py`, remove redundant legacy probe aliases and transitional parameter mappings.
   - Standardize on explicit configuration models for OpenAI-compatible, Ollama, and mock inference engines.
2. **Clean Up Consumer Message Adapters**:
   - In `services/inference_worker/src/inference_worker/redis_consumer.py`, remove legacy schema translation fallbacks and enforce the canonical event schema.
3. **Prune Package Root Exports**:
   - In `services/inference_worker/src/inference_worker/__init__.py`, verify that only authoritative client and consumer interfaces are exported.
4. **Update Blackbox Test Suites**:
   - Verify tests in `tests/test_inference_worker*` pass cleanly using canonical backend configurations.

## INVEST Criteria Evaluation
- **Independent (I)**: Changes are strictly self-contained within `services/inference_worker`.
- **Negotiable (N)**: Clean standard Python configuration and typing.
- **Valuable (V)**: Streamlines LLM inference pipeline and eliminates dead fallback branches.
- **Estimable (E)**: Scoped to `config.py`, `llm_client.py`, and `redis_consumer.py`.
- **Small (S)**: File changes well under 50 lines.
- **Testable (T)**: Verified via `uv run pytest tests/test_inference_worker*`.

## Definition of Done
1. Legacy fallback configurations and parameter shims removed.
2. Redis consumer enforces canonical event schema without transitional translation fallbacks.
3. Package exports pruned of any deprecated aliases.
4. All inference worker tests pass with zero warnings.
