---
id: '0766'
title: Dynamic Tool Handlers Run Without In-Process Exec
status: Complete
created: 2026-11-17
dependencies:
- TASK-0545
- TASK-0727
governing_adrs:
- ADR-0001
- ADR-0015
governing_prds: []
governing_stories: []
target_bc: gateway_mcp
target_release: 0.9.0
---

# TASK-0766: Dynamic Tool Handlers Run Without In-Process Exec

## Status
Complete

## Summary
Registered dynamic tools carry Python `handler_code`. The MCP gateway runs it with `exec` in its
own process. An AST check and a reduced builtins table are the only protection. Restricted
`exec` sandboxes in CPython are often escaped, so one registered tool can run arbitrary code with
the gateway's credentials (including the service credential from TASK-0689).

## Problem Statement
- `gateway/mcp/src/gateway_mcp/sandbox.py:144-170`: `execute_sandboxed_handler` calls
  `exec(code_str, safe_globals, local_ns)` and then calls the first callable it finds.
- The handler runs in the request path of the MCP process.

## Documentation & Architecture Review
- ADR-0001: `mcp_tool.manage` and `mcp_tool.execute` gate who registers and runs a tool. They do
  not make the code safe.
- ADR-0015: no hidden risk behind a fallback.
- `docs/how-to/import-universal-vtt-maps-and-register-dynamic-tools.md` documents dynamic tools.

## Product & User Story References
None. Security.

## Detailed Specification & Implementation Plan
1. Spike (write an ADR in `docs/project/adrs/`): choose one design.
   - Option A (recommended): declarative handlers. A tool definition is data (a template, dice
     expressions, and calls to existing registered tools with mapped arguments). No user code
     runs.
   - Option B: an isolated runtime (separate process or container with no network, no secrets,
     CPU and memory limits, and a time-out).
2. Implement the chosen design. Delete `sandbox.py` `exec` and the code-string field. No
   compatibility path for code handlers (DoR 9).
3. Update the dynamic-tool how-to and the FastMCP gateway reference.

## Frontdoor Blackbox Test Plan
- Register a tool through the public route with a declarative handler (or isolated runtime).
  Execute it. Assert the result.
- Register a tool that tries to read an environment variable or open a socket. Assert the
  registration is refused (Option A) or the call fails with no secret in the output (Option B).

## Definition of Done
- No `exec` or `eval` of user input remains in `gateway/mcp`.
- The ADR records the decision.
- `uv run pytest`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: high
- Source audits: `work/0545.md`, `reports/refactor-r1/gateway-mcp.md`
