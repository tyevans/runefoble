---
id: '0041'
title: FastMCP Gateway Server Modular Decomposition
status: Complete
created: 2026-09-25
dependencies:
- TASK-0005
- TASK-0020
governing_adrs:
- ADR-0002
- ADR-0007
- ADR-0009
target_release: 0.2.0
pr_url: https://github.com/tyevans/runefoble/pull/30
---
# TASK-0041: FastMCP Gateway Server Modular Decomposition

## Status
Refined

## Summary
Decompose the monolithic FastMCP gateway server entrypoint in `gateway/mcp/src/gateway_mcp/server.py` (433 lines, 86.6% of limit) into modular, single-responsibility sub-modules organized into `tools/`, `resources/`, and `prompts/` before it breaches Hard Invariant 6 (File length limit < 500 lines).

## Problem Statement
Health scans identify `gateway/mcp/src/gateway_mcp/server.py` (433 lines) as a high-risk refactoring candidate. It currently bundles:
- Tabletop dice rolling, board token movement, and spatial queries.
- Character sheet statistics, HP modifications, condition mutations, and spellcasting tools.
- Dynamic FastMCP resource providers (`session://active`, `encounter://current`).
- LLM prompt templates (`dm_narrative_guidance`, `tactical_action_adviser`).

As upcoming Milestone 2 and Milestone 3 features introduce compendium queries, RAG lookups, and DM copilot tools, this file will rapidly exceed the 500-line ceiling if not partitioned.

## INVEST Criteria Evaluation
- **Independent (I)**: Refactors internal module layout without modifying external FastMCP tool schemas, prompt templates, or resource URI contracts.
- **Negotiable (N)**: Sub-module organization and registration hook signatures can be refined for ergonomic registration.
- **Valuable (V)**: Protects against Hard Invariant 6 breaches (<500 lines) and enables clean expansion of tabletop agent tools for autonomous DMing.
- **Estimable (E)**: Standard FastMCP modularization pattern registering decorators onto an imported or passed `FastMCP` application instance.
- **Small (S)**: Scope strictly isolated to `gateway/mcp/src/gateway_mcp/`; all resulting modules remain under 200 lines.
- **Testable (T)**: Existing blackbox integration test suites (`tests/test_mcp_tools.py`, `tests/test_blackbox_mcp_gateway.py`) verify zero regression via public MCP protocol calls.

## Governing Architecture & ADRs
- **ADR-0002**: Event-Driven Watcher Gameplay Orchestration (MCP tools invoke tabletop domain services and emit CloudEvents).
- **ADR-0007**: Domain-Driven Design Architecture (bounded context separation between gateway and backend microservices).
- **ADR-0009**: Code Quality and Linting with Ruff and Pre-Commit (strict file length invariant < 500 lines).

## Proposed Decomposition
1. **Module Hierarchy (`gateway/mcp/src/gateway_mcp/`)**:
   - `tools/dice.py`: `roll_dice` tool implementation (< 100 lines).
   - `tools/board.py`: `inspect_tactical_board`, `move_board_token` tools (< 150 lines).
   - `tools/character.py`: `get_character_sheet`, `modify_character_hp`, `cast_spell`, `apply_condition` tools (< 180 lines).
   - `resources/session.py`: `get_active_session_context`, `get_combat_encounter_state` resource handlers (< 120 lines).
   - `prompts/narrative.py`: `dm_narrative_guidance`, `tactical_action_adviser` prompt templates (< 120 lines).
2. **Server Orchestration Shell (`gateway/mcp/src/gateway_mcp/server.py`)**:
   - Reduce `server.py` to a thin orchestration shell (< 60 lines) initializing `mcp = FastMCP("Runefoble MCP Gateway")` and mounting tool, resource, and prompt registration functions.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **FastMCP Modular Architecture**:
   - `tools/`, `resources/`, and `prompts/` sub-packages created with registration entrypoints invoked by `server.py`.
2. **Contract Preservation**:
   - Zero changes to public FastMCP tool names (`roll_dice`, `inspect_tactical_board`, `move_board_token`, `get_character_sheet`, `modify_character_hp`, `cast_spell`, `apply_condition`), resource URIs (`session://active`, `encounter://current`), or prompt templates.
3. **File Length Compliance**:
   - Every source file in `gateway/mcp/src/` strictly under 200 lines (well below the 500-line ceiling).
4. **Blackbox Frontdoor Test Verification**:
   - 100% test pass rate across `tests/test_mcp_tools.py` and `tests/test_blackbox_mcp_gateway.py`.
5. **Quality Gate Verification**:
   - Passes `uv run ruff check .` and `uv run ruff format --check .`.
