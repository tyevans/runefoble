---
id: '0449'
title: The Watcher Intent Middleware Interceptor Pipeline & OpenTelemetry Tracing
status: Proposed
created: 2026-09-29
dependencies:
- TASK-0448
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

# TASK-0449: The Watcher Intent Middleware Interceptor Pipeline & OpenTelemetry Tracing

## Status
Proposed

## Summary
Implement a composable intent middleware interceptor pipeline in `services/the_watcher` (`the_watcher/middleware/`) allowing developers and plugins to register pre-parse and post-parse hooks that inspect, sanitize, augment, or validate speech transcripts and structured action intents before board execution, with end-to-end OpenTelemetry span instrumentation for latency profiling per US-0032.

## Problem Statement
Intent extraction in `the_watcher` currently transitions directly from raw audio transcript to parsed action. Developers cannot inject custom domain middleware (such as entity alias normalization, profanity sanitization, campaign-specific keyword substitution, or custom rule validation) without modifying internal parsers. Furthermore, without fine-grained latency profiling across intermediate extraction stages, developers cannot identify bottlenecks in external LLM calls or complex intent transformations.

## Governing Architecture & ADRs
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean module layout in `services/the_watcher`.
- **ADR-0007: Domain-Driven Design Architecture**: Middleware pipeline decouples preprocessing and postprocessing from core domain aggregates.
- **ADR-0008: Distributed Tracing with OpenTelemetry**: OpenTelemetry spans wrap each middleware hook with execution time and attribute metadata.
- **ADR-0010: Developer Experience & Tooling**: Configurable middleware chain via standard dependency injection.

## Product & User Story References
- [`prd-0001-the-watcher-ai-dm-and-board-animator.md`](../../product/accepted/prd-0001-the-watcher-ai-dm-and-board-animator.md)
- [`us-0001-player-commands-board-via-voice.md`](../../user_stories/accepted/us-0001-player-commands-board-via-voice.md)
- [`us-0032-custom-llm-provider-injection-and-intent-middleware.md`](../../user_stories/accepted/us-0032-custom-llm-provider-injection-and-intent-middleware.md)

## Scope of Work
1. **Middleware Pipeline Core (`the_watcher/middleware/pipeline.py`)**:
   - Define `PreParseHook` (`(transcript: str, context: dict) -> Tuple[str, dict]`) and `PostParseHook` (`(intent: IntentResult, context: dict) -> IntentResult`).
   - Implement `IntentMiddlewarePipeline` managing registered hooks, sequential execution, and short-circuit error handling.
2. **Built-in Middleware Hooks (`the_watcher/middleware/hooks.py`)**:
   - `AliasNormalizationHook`: Replaces character nicknames and party aliases with canonical entity IDs.
   - `ProfanitySanitizerHook`: Strips or masks offensive terms from narration logs while preserving tactical commands.
   - `TacticalBoundaryGuardHook`: Asserts destination coordinates are within map bounds prior to board state dispatch.
3. **OpenTelemetry Span Instrumentation (`the_watcher/middleware/tracing.py`)**:
   - Wrap each hook invocation in an active OpenTelemetry span (`the_watcher.middleware.{hook_name}`) recording duration and status.
4. **Integration with TheWatcherEngine (`the_watcher/watcher_ai.py`)**:
   - Wire `IntentMiddlewarePipeline` into `TheWatcherEngine.parse_speech_intent` and `parse_compound_intent`.

## Definition of Done
1. Middleware pipeline executes registered pre-parse and post-parse hooks in deterministic registration order.
2. Built-in hooks strictly < 100 lines each per Hard Invariant 6.
3. OpenTelemetry spans recorded for all hook executions with zero unhandled exceptions.
4. 100% test coverage in `services/the_watcher/tests/test_middleware_pipeline.py`.
5. Code passes `uv run ruff check .` and `uv run ruff format --check .`.
