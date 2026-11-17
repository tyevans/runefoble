---
id: '0606'
title: Gateway MCP Dynamic Tools Use Real Event Bus and Reject Handler-Less Definitions
status: Refined
created: 2026-11-17
dependencies: []
governing_adrs:
- ADR-0006
- ADR-0011
- ADR-0014
governing_prds:
- PRD-0022
governing_stories:
- US-0035
target_release: 0.9.0
severity: high
source_audits:
- w1-gateway-mcp.md
---

# TASK-0606: Gateway MCP Dynamic Tools Use Real Event Bus and Reject Handler-Less Definitions

## Status
Refined

## Summary
Two fake behaviours in the dynamic tool path. First, dynamic tool events go to an in-memory mock Redis bus in production, and failures are dropped silently. Second, a dynamic tool with no handler returns a fixed success echo. This task injects the real Redis Streams bus at gateway startup, logs dropped events, and rejects tool definitions without a handler or proxy target.

## Problem Statement
- `gateway/mcp/src/gateway_mcp/dynamic/events.py:14-25`: `get_event_bus` falls back to `RedisStreamsEventBus(client=MockAsyncRedis())` when no bus is set.
- `gateway/api/src/gateway_api/main.py` sets only the platform bus, not the gateway MCP bus.
- `events.py:36-40`: `safe_dispatch_event` drops the event on `RuntimeError` without a log.
- Result: `DynamicToolRegisteredEvent`, `DynamicToolUnregisteredEvent` and `DynamicToolInvokedEvent` never reach `runefoble:events:system` in deployment.
- `dynamic/registry.py:108-112`: a tool without `handler_code` returns `{"status": "success", "executed": True}`.

Source: `.audit/reports/w1-gateway-mcp.md` F4 and F12.

## Documentation & Architecture Review
- `docs/reference/redis-streams-event-bus.md`: stream names and consumer contract.
- `docs/reference/events-schema.md`: dynamic tool events.
- ADR-0006: Redis Streams is the transport. Production must publish.
- Note: TASK-0489 (refined, shims) covers `dynamic_registry.py` for shims. Coordinate the merge on that file.

## Product & User Story References
- `docs/project/user_stories/accepted/us-0035-runtime-mcp-tool-hot-reloading-and-extension-slots.md`
- `docs/project/product/accepted/prd-0022-extensible-modder-platform-and-mcp-registry.md`

## Detailed Specification & Implementation Plan
1. Gateway startup (`gateway/api/src/gateway_api/main.py`) builds the Redis Streams bus from platform settings and calls the gateway MCP `set_event_bus`.
2. Remove the `MockAsyncRedis` fallback from `dynamic/events.py`. If no bus is set, raise at startup.
3. Replace the silent drop with a logged error and an OpenTelemetry span event.
4. At registration, reject definitions with empty `handler_code` and no proxy URL (HTTP 422 on the REST route).
5. Update the fastmcp-gateway reference and the event schema if they list the mock behaviour.

## Frontdoor Blackbox Test Plan
- Before fix: register a dynamic tool through the REST route, then read the system stream through the public Redis consumer. No event is found (test fails).
- After fix: the same registration produces `DynamicToolRegisteredEvent` on `runefoble:events:system`.
- After fix: registering a tool with no handler returns 422 and no tool is added.
- After fix: invoking a dynamic tool produces `DynamicToolInvokedEvent` on the stream.

## Definition of Done
1. `MockAsyncRedis` is not referenced in `gateway/mcp` or `gateway/api` production code.
2. Silent drop removed. Files under 500 lines.
3. Blackbox tests pass. Gateway MCP and dynamic tool suites pass.
4. Ruff check and format pass.
5. Reference docs and `CHANGELOG.md` `[Unreleased]` updated.
