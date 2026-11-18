---
id: '0748'
title: MCP Package Drops Re-Exports, the Dead Entrypoint, and Stale Documentation Claims
status: Refined
created: 2026-11-17
dependencies:
- TASK-0629
governing_adrs:
- ADR-0015
governing_prds:
- PRD-0022
governing_stories:
- US-0008
target_bc: gateway
target_release: 0.9.0
---
# TASK-0748: MCP Package Drops Re-Exports, the Dead Entrypoint, and Stale Documentation Claims

## Status
Refined. Found by the refactor audit round refactor-r1 and checked against the code on 2026-11-17.

## Summary
Seven `__init__.py` files re-export names, a dead `main.py` prints a greeting, the README is empty, and several docs cite wrong files and ADRs.

## Problem Statement
- Re-exports: `server.py:78-102` (`__all__`, 25 names), `tools/__init__.py:5-63`, `dynamic/__init__.py:3-37`, `resources/__init__.py:5-19`, `prompts/__init__.py:5-19`, `clients/__init__.py:3-15`, `routers/__init__.py:3-5`.
- `gateway/mcp/main.py:1-6` prints "Hello from gateway-mcp!" and nothing runs it. `gateway/mcp/README.md` has 0 lines.
- `docs/reference/fastmcp-gateway.md` says `server.py` is under 100 lines (it is 119). `sandbox.py:4` and the reference page cite ADR-0008 as the FastMCP architecture. ADR-0008 covers property and mutation testing.
- `docs/how-to/add-a-watcher-ai-tool.md:51` runs `gateway/mcp/src/gateway_mcp/main.py` by path. The reference page uses `python -m gateway_mcp.main`.
- `docs/project/backlog/refined/0629-*.md` cites `server.py:48`, a line that no longer holds that code.

## Documentation & Architecture Review
- AGENTS.md hard invariants and DoR 9 (no compatibility shims).
- ADR-0015.
- TASK-0629 adds the package marker with no re-exports. TASK-0745 deletes `clients/`: skip `clients/__init__.py` if it is gone.

## Product & User Story References
- PRD-0022
- US-0008

## Detailed Specification & Implementation Plan
1. Make each `__init__.py` a docstring only. Import from the defining module at every call site (`server.py`, `gateway_api/main.py` if still present, tests).
2. Delete `gateway/mcp/main.py`. Write a short README or delete it.
3. Correct the four doc claims and the ADR citations. Correct the path in the how-to. Update the TASK-0629 text.

## Frontdoor Blackbox Test Plan
- Existing suites pass. `tests/test_blackbox_gateway_mcp_http.py:116` (`python -m gateway_mcp.main`) still passes.
- `grep` finds no re-export name outside its defining module and no reference to the deleted file.

## Definition of Done
- No `__all__` list of tool names remains in `server.py`.
- `uv run pytest`, `make lint`, and `make health-check` pass. No file over 500 lines.
- Docs touched by the change are correct. `CHANGELOG.md` has an `[Unreleased]` entry.

## Audit Provenance
- Severity: low
- Source audits: `gateway-mcp.md (F7, F9)`
