---
id: '0737'
title: Dynamic Tool Handlers Run With a Time Limit and Do Not Block the Event Loop
status: Refined
created: 2026-11-17
dependencies:
- TASK-0545
governing_adrs:
- ADR-0015
governing_prds:
- PRD-0022
governing_stories:
- US-0035
target_bc: gateway
target_release: 0.9.0
---
# TASK-0737: Dynamic Tool Handlers Run With a Time Limit and Do Not Block the Event Loop

## Status
Refined. Found by the refactor audit round refactor-r1 and checked against the code on 2026-11-17.

## Summary
A dynamic tool handler runs synchronously inside the async event loop with no time limit. A long loop blocks the whole MCP server, including `/healthz` and every other session.

## Problem Statement
- `gateway/mcp/src/gateway_mcp/dynamic/builder.py:34-37` is an `async def` that calls `registry.execute_tool(...)`.
- `dynamic/registry.py:95-107` runs `execute_sandboxed_handler` synchronously. `sandbox.py:144-169` calls the handler with no timeout.

## Documentation & Architecture Review
- AGENTS.md hard invariants and DoR 9 (no compatibility shims).
- ADR-0015.
- TASK-0545 says a separate task must remove the sandbox `exec` at `sandbox.py:155`. No task owns that today (see the index). Choose the isolation form here only after that decision. A thread cannot stop a runaway loop. A subprocess can.

## Product & User Story References
- PRD-0022
- US-0035

## Detailed Specification & Implementation Plan
1. Run the handler in a subprocess with a hard time limit (default 5 s, a named setting). On timeout, kill the process and return a tool error.
2. If the owner of the `exec` removal decides on another isolation model, follow it and keep the limit.
3. Do not block the event loop at any point.

## Frontdoor Blackbox Test Plan
- Register a handler with `while True: pass` through the public admin route. Call it over MCP. Assert a tool error within about 2 s of the limit, and that `/healthz` answers during the call.

## Definition of Done
- No dynamic handler runs on the event loop thread.
- `uv run pytest`, `make lint`, and `make health-check` pass. No file over 500 lines.
- Docs touched by the change are correct. `CHANGELOG.md` has an `[Unreleased]` entry.

## Audit Provenance
- Severity: medium
- Source audits: `gateway-mcp.md (F10)`
