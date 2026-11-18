---
id: '0736'
title: MCP Exposes One Condition Tool
status: Refined
created: 2026-11-17
dependencies: []
governing_adrs:
- ADR-0015
governing_prds:
- PRD-0022
governing_stories:
- US-0008
target_bc: gateway
target_release: 0.9.0
---
# TASK-0736: MCP Exposes One Condition Tool

## Status
Refined. Found by the refactor audit round refactor-r1 and checked against the code on 2026-11-17.

## Summary
`add_condition` and `apply_condition` have the same body and docstring, and both are registered. DoR 9 forbids aliases.

## Problem Statement
- `gateway/mcp/src/gateway_mcp/tools/character.py:104-121` defines both functions with the same body. Both are registered at `:152-153`.
- `docs/reference/fastmcp-gateway.md` says both tools share one route. TASK-0489 (complete) kept both.

## Documentation & Architecture Review
- AGENTS.md hard invariants and DoR 9 (no compatibility shims).
- ADR-0015.
- Update `docs/reference/fastmcp-gateway.md`, `docs/how-to/add-a-watcher-ai-tool.md`, and any prompt in `gateway/mcp/src/gateway_mcp/prompts/` that names the removed tool.

## Product & User Story References
- PRD-0022
- US-0008

## Detailed Specification & Implementation Plan
1. Keep `apply_condition` (the name that matches the domain event) and remove `add_condition` from the module, `register_character_tools`, `tools/__init__.py`, and `server.py`. If grep shows `add_condition` is the name in the prompts and tests, keep it instead. Pick one and update all call sites.

## Frontdoor Blackbox Test Plan
- MCP `tools/list` shows exactly one condition tool. `tools/call` on it still returns `condition_applied`.

## Definition of Done
- `grep` finds no reference to the removed tool name in the repository.
- `uv run pytest`, `make lint`, and `make health-check` pass. No file over 500 lines.
- Docs touched by the change are correct. `CHANGELOG.md` has an `[Unreleased]` entry.

## Audit Provenance
- Severity: low
- Source audits: `gateway-mcp.md (F6)`
