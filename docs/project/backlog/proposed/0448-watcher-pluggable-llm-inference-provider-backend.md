---
id: '0448'
title: The Watcher Pluggable LLM Inference Provider Backend & Endpoint Router
status: Proposed
created: 2026-09-29
dependencies:
- TASK-0002
- TASK-0039
governing_adrs:
- ADR-0003
- ADR-0007
- ADR-0010
governing_prds:
- PRD-0001
governing_stories:
- US-0001
- US-0032
target_release: 0.9.0
---

# TASK-0448: The Watcher Pluggable LLM Inference Provider Backend & Endpoint Router

## Status
Proposed

## Summary
Implement a pluggable LLM inference provider interface and dynamic endpoint router in `services/the_watcher` (`the_watcher/providers/`), allowing `the_watcher` to route speech transcription and intent extraction requests to configurable LLM endpoints (OpenAI-compatible, Ollama, self-hosted vLLM, and local deterministic mock) with configurable timeouts, retries, and fallback fallbacks per US-0032.

## Problem Statement
Currently, `the_watcher` uses a fixed deterministic movement and action parser. While fast (<5ms), it lacks the ability to delegate complex or unstructured player speech to external LLMs (such as Ollama or OpenAI-compatible inference servers) when natural conversational phrasing does not match predefined grammar patterns. Furthermore, developers and DM hosts cannot inject their own fine-tuned models or local endpoints without modifying core service internals.

## Governing Architecture & ADRs
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean package architecture in `services/the_watcher`.
- **ADR-0007: Domain-Driven Design Architecture**: Encapsulation of external inference adapters behind a domain interface (`LLMProviderInterface`).
- **ADR-0010: Developer Experience & Tooling**: Local zero-dependency mock provider by default for CI and local dev.

## Product & User Story References
- [`prd-0001-the-watcher-ai-dm-and-board-animator.md`](../../product/accepted/prd-0001-the-watcher-ai-dm-and-board-animator.md)
- [`us-0001-player-commands-board-via-voice.md`](../../user_stories/accepted/us-0001-player-commands-board-via-voice.md)
- [`us-0032-custom-llm-provider-injection-and-intent-middleware.md`](../../user_stories/accepted/us-0032-custom-llm-provider-injection-and-intent-middleware.md)

## Scope of Work
1. **Provider Protocol & Models (`the_watcher/providers/base.py`)**:
   - Define `LLMProviderInterface` abstract protocol (`complete`, `stream_intent`, `health_check`).
   - Define provider configuration schemas: `ProviderConfig` (provider_type, base_url, api_key, model_name, timeout_ms, max_retries).
2. **OpenAI-Compatible Adapter (`the_watcher/providers/openai_compatible.py`)**:
   - Implement HTTP client communicating with standard `/v1/chat/completions` API (compatible with vLLM, LiteLLM, Ollama, and OpenAI).
3. **Ollama Native Adapter (`the_watcher/providers/ollama.py`)**:
   - Implement lightweight client for local Ollama `/api/chat` endpoints with model availability checks.
4. **Mock Provider (`the_watcher/providers/mock.py`)**:
   - Provide sub-10ms deterministic mock provider for unit and integration testing without external network calls.
5. **Provider Router & Fallback Chain (`the_watcher/providers/router.py`)**:
   - Dynamically instantiate provider based on campaign or global environment configuration.
   - Implement automatic fallback to deterministic regex parser if external inference fails or exceeds 500ms timeout budget.

## Definition of Done
1. `LLMProviderInterface` implemented with OpenAI, Ollama, and Mock adapters strictly < 120 lines each.
2. Fallback mechanism guarantees intent extraction completes within 500ms budget under network delays.
3. Unit tests achieve 100% coverage across provider implementations in `services/the_watcher/tests/`.
4. Code passes `uv run ruff check .` and `uv run ruff format --check .`.
