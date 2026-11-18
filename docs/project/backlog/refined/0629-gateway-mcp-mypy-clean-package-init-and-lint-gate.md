---
id: '0629'
title: Make mypy Pass on gateway/mcp and Add It to the Lint Gate
status: Refined
created: 2026-11-17
dependencies:
- TASK-0489
governing_adrs:
- ADR-0009
- ADR-0010
governing_prds:
- PRD-0022
governing_stories: []
target_release: 0.9.0
---

# TASK-0629: Make mypy Pass on gateway/mcp and Add It to the Lint Gate

## Status
Refined

## Summary
`uv run mypy gateway/mcp/src/gateway_mcp` reports 44 errors in 17 files. Most come from a missing `src/gateway_mcp/__init__.py`, which makes the package a namespace package. The rest come from a `FastMCP.get_tool` monkeypatch in `server.py:48`. Add the package marker, replace the monkeypatch with the public FastMCP lookup, and add mypy to the lint gate for this package.

## Problem Statement
- `gateway/mcp/src/gateway_mcp/__init__.py` does not exist (`.audit/reports/w1-gateway-mcp.md` F14).
- `server.py:48`: `mcp.get_tool = mcp._tool_manager.get_tool` monkeypatches a private attribute; the errors at `dynamic/registry.py:47,79` come from it (F7).
- `make lint` runs ruff only (Makefile lint target).

## Documentation & Architecture Review
- Overlap: TASK-0489 deletes `dynamic_registry.py` and the `apply_condition` alias and widens its scope to the `get_tool` monkeypatch. This task must not duplicate that: TASK-0489 owns the monkeypatch removal. This task owns the package marker, the remaining typing errors, and the lint gate.
- ADR-0009, ADR-0010 for the gate.

## Product & User Story References
- PRD-0022 (modder platform and MCP registry).

## Detailed Specification & Implementation Plan
1. Add `gateway/mcp/src/gateway_mcp/__init__.py` with a module docstring only (no re-exports, per DoR 9).
2. After TASK-0489 lands, re-run `uv run mypy gateway/mcp/src/gateway_mcp`. Fix the remaining errors by typing, not ignores.
3. Add the mypy command for `gateway/mcp/src/gateway_mcp` to the Makefile lint target.
4. If TASK-0489 has not landed, stop and sequence after it.

## Frontdoor Blackbox Test Plan
- Before fix: `uv run mypy gateway/mcp/src/gateway_mcp` exits 1 with 44 errors.
- After fix: exits 0; `make lint` runs it; the existing MCP blackbox tests (`tests/test_blackbox_mcp_gateway.py`) still pass.

## Definition of Done
1. mypy passes for gateway/mcp with no ignores.
2. Lint gate includes it.
3. TASK-0489 is complete before this task closes.
4. No file above 500 lines.

## Audit Provenance

- Severity: low
- Source audits: `w1-gateway-mcp.md`
