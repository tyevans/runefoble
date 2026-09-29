---
id: '0450'
title: Custom LLM Inference and Intent Middleware Blackbox Test Suite
status: Proposed
created: 2026-09-29
dependencies:
- TASK-0448
- TASK-0449
governing_adrs:
- ADR-0003
- ADR-0007
- ADR-0008
- ADR-0010
governing_prds:
- PRD-0001
governing_stories:
- US-0001
- US-0032
target_release: 0.9.0
---

# TASK-0450: Custom LLM Inference and Intent Middleware Blackbox Test Suite

## Status
Proposed

## Summary
Implement a comprehensive blackbox test suite under `tests/test_blackbox_custom_llm_and_middleware.py` verifying external LLM provider routing, custom Ollama/OpenAI-compatible endpoint invocation, fallback to deterministic parser on timeout, pre/post intent middleware hook execution, and OpenTelemetry span propagation per Hard Invariant 7.

## Problem Statement
With the addition of pluggable LLM backends (TASK-0448) and intent middleware pipelines (TASK-0449), the system requires an end-to-end blackbox test suite to ensure that:
1. Custom inference provider endpoints receive properly formatted messages.
2. Network timeouts or malformed LLM responses gracefully fall back to deterministic regex parsing without disrupting the sub-500ms voice pipeline.
3. Pre-parse and post-parse middleware hooks run in proper order and modify actions predictably.
4. OpenTelemetry spans are published with latency timings and expected attributes.

## Governing Architecture & ADRs
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean test execution using root `uv run pytest`.
- **ADR-0007: Domain-Driven Design Architecture**: Blackbox testing through public API frontdoors without manipulating internal private state.
- **ADR-0008: Distributed Tracing with OpenTelemetry**: OpenTelemetry memory exporter validation for emitted spans.
- **ADR-0010: Developer Experience & Tooling**: Rapid, deterministic blackbox test execution.

## Product & User Story References
- [`prd-0001-the-watcher-ai-dm-and-board-animator.md`](../../product/accepted/prd-0001-the-watcher-ai-dm-and-board-animator.md)
- [`us-0001-player-commands-board-via-voice.md`](../../user_stories/accepted/us-0001-player-commands-board-via-voice.md)
- [`us-0032-custom-llm-provider-injection-and-intent-middleware.md`](../../user_stories/accepted/us-0032-custom-llm-provider-injection-and-intent-middleware.md)

## Scope of Work
1. **Frontdoor Test Client & Mock HTTP Server Setup**:
   - Spin up lightweight mock HTTP server simulating OpenAI `/v1/chat/completions` and Ollama `/api/chat` endpoints.
   - Configure frontdoor `TestClient` targeting `/api/watcher/intent/speech` and `/api/watcher/intent/compound`.
2. **Pluggable Provider Routing Scenarios**:
   - Verify valid LLM response returns structured `IntentResult`.
   - Verify simulated 600ms latency triggers fallback to deterministic movement parser within 500ms total budget.
   - Verify HTTP 500 / connection error from custom endpoint triggers fallback with warning log.
3. **Middleware Pipeline Scenarios**:
   - Verify `AliasNormalizationHook` replaces aliases before passing to parser.
   - Verify `ProfanitySanitizerHook` sanitizes transcript without modifying tactical keywords.
   - Verify `TacticalBoundaryGuardHook` clamps or validates out-of-bounds target coordinates.
4. **OpenTelemetry Latency Spans Verification**:
   - Use in-memory OpenTelemetry span exporter to assert spans: `the_watcher.llm_provider`, `the_watcher.middleware.pre_parse`, `the_watcher.middleware.post_parse`.
5. **Invariant Compliance**:
   - Keep `tests/test_blackbox_custom_llm_and_middleware.py` strictly < 300 lines per Hard Invariant 6.

## Definition of Done
1. Blackbox test suite covers pluggable provider routing, timeout fallbacks, middleware chain, and OTel spans.
2. 100% of test scenarios pass via `uv run pytest tests/test_blackbox_custom_llm_and_middleware.py`.
3. Test file length is strictly < 300 lines per Hard Invariant 6.
4. Code passes `uv run ruff check .` and `uv run ruff format --check .`.
