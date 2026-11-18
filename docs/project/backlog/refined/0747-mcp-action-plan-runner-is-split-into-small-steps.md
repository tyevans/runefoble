---
id: '0747'
title: MCP Action Plan Runner Is Split Into Validate, Map, and Propose Steps
status: Refined
created: 2026-11-17
dependencies:
- TASK-0746
governing_adrs:
- ADR-0015
governing_prds:
- PRD-0022
governing_stories:
- US-0008
target_bc: gateway
target_release: 0.9.0
---
# TASK-0747: MCP Action Plan Runner Is Split Into Validate, Map, and Propose Steps

## Status
Refined. Found by the refactor audit round refactor-r1 and checked against the code on 2026-11-17.

## Summary
`execute_agent_action_plan` is 104 lines. It mixes validation, parameter mapping, and HTTP proposing, and it finds tools through a global that can be `None`. When it is `None`, every step fails with a vague message.

## Problem Statement
- `gateway/mcp/src/gateway_mcp/tools/orchestration.py:42-145`. The `_fail` closure (`:57-78`) builds the error shape. Tool existence uses `_mcp_instance._tool_manager.get_tool` (`:85-89`). Parameter extraction has three fallback keys (`:81`, `:95-104`).

## Documentation & Architecture Review
- AGENTS.md hard invariants and DoR 9 (no compatibility shims).
- ADR-0015.
- `docs/reference/fastmcp-gateway.md` (orchestration tool).

## Product & User Story References
- PRD-0022
- US-0008

## Detailed Specification & Implementation Plan
1. Add `tools/plan.py` with `plan_step(action) -> StepRequest`, `validate_step(...)`, and `run_plan(steps, propose)`.
2. Pass a `ToolCatalog` port (callable returning tool names) from the container (TASK-0746). Pass the Watcher call as a port.
3. Keep one parameter key per field. Keep the response shape: `tests/test_blackbox_mcp_orchestration_and_resources.py` pins it.

## Frontdoor Blackbox Test Plan
- Through MCP: (a) unknown tool name, (b) missing `actor_name`, (c) two valid steps. Assert step numbers and `failed_step`, and that the Watcher receives no request after a failed step.

## Definition of Done
- No function in `orchestration.py` or `plan.py` is over 60 lines.
- `uv run pytest`, `make lint`, and `make health-check` pass. No file over 500 lines.
- Docs touched by the change are correct. `CHANGELOG.md` has an `[Unreleased]` entry.

## Audit Provenance
- Severity: low
- Source audits: `gateway-mcp.md (F4)`
