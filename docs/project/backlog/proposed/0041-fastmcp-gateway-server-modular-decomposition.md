---
id: '0041'
title: FastMCP Gateway Server Modular Decomposition
status: Proposed
created: 2026-09-25
dependencies: [TASK-0005, TASK-0020]
governing_adrs: [ADR-0007, ADR-0009]
target_release: 0.2.0
---

# TASK-0041: FastMCP Gateway Server Modular Decomposition

## Status
Proposed

## Summary
Decompose monolithic FastMCP gateway entrypoint in `gateway/mcp/src/gateway_mcp/server.py` (427 lines, approaching the 500-line invariant) into modular FastMCP sub-modules organized into `tools/`, `resources/`, and `prompts/`.

## Problem Statement
Health scans identify `gateway/mcp/src/gateway_mcp/server.py` (427 lines, 85.4% of limit) as a high-risk refactoring candidate. It currently bundles:
- Tabletop dice rolling, board token movement, and spatial queries.
- Character sheet stats, conditions, and spellcasting tools.
- FastMCP dynamic resources (`session://active`, `encounter://current`).
- LLM system prompts (`dm_narrative_guidance`, `tactical_action_adviser`).

As additional tabletop actions and rules compendiums are introduced, this file will breach Hard Invariant 6 (File length limit < 500 lines).

## Proposed Decomposition
1. **Module Hierarchy (`gateway/mcp/src/gateway_mcp/`)**:
   - `tools/`:
     - `dice.py`: `roll_dice` tool.
     - `board.py`: `inspect_tactical_board`, `move_board_token` tools.
     - `character.py`: `get_character_sheet`, `modify_character_hp`, `cast_spell`, `apply_condition` tools.
   - `resources/`:
     - `session.py`: `get_active_session_context`, `get_combat_encounter_state` resource handlers.
   - `prompts/`:
     - `narrative.py`: `dm_narrative_guidance`, `tactical_action_adviser` prompt templates.
2. **Server Orchestration Shell (`gateway/mcp/src/gateway_mcp/server.py`)**:
   - Reduce `server.py` to a thin initialization module (< 50 lines) that instantiates `FastMCP("Runefoble MCP Gateway")` and registers tools/resources/prompts via clean registration hooks.

## Acceptance Criteria
1. Zero changes to public FastMCP tool schemas, resource URIs, or prompt signatures.
2. Every file in `gateway/mcp/src/` strictly under 200 lines.
3. 100% test pass rate across all FastMCP tests (`tests/test_mcp_tools.py`, `tests/test_blackbox_mcp_gateway.py`).
4. Conforms to Hard Invariant 6 (< 500 lines per file).
