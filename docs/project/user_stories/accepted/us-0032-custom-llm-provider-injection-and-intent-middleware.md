---
id: 0032
title: Custom LLM Provider Injection and Intent Middleware Interceptors
status: Accepted
created: 2026-09-25
governing_prd: PRD-0001
---

# US-0032 — Custom LLM Provider Injection and Intent Middleware Interceptors

## Governing PRD
- [`PRD-0001: The Watcher AI Dungeon Master and Real-Time Board Animator`](../../product/accepted/prd-0001-the-watcher-ai-dm-and-board-animator.md)

## User Story

**As a** platform developer and AI engineer (Alex),  
**I want to** configure custom LLM inference endpoints and register middleware interceptors on the intent pipeline,  
**So that** I can experiment with fine-tuned open-source models, custom system prompts, and custom intent pre-processors.

## Acceptance Criteria

1. **Pluggable Inference Backends**: The inference worker supports dynamic routing to custom OpenAI-compatible and Ollama endpoints via configuration.
2. **Intent Middleware Pipeline**: Developers can register pre-parse and post-parse hooks that modify or augment structured actions before board execution.
3. **Traceability**: All middleware executions are instrumented with OpenTelemetry spans for latency profiling.
