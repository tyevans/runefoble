---
id: 0020
title: FastMCP Agent Tool Loop & Session State Context Server
status: Refined
created: 2026-09-25
dependencies: [TASK-0005, TASK-0010, TASK-0016]
governing_adrs: [ADR-0007, ADR-0011]
target_release: 0.1.0
---

# TASK-0020 — FastMCP Agent Tool Loop & Session State Context Server

## Summary
Implement automated multi-turn tool loops, dynamic session context resources (`session://{session_id}/state`), and encounter state aggregation within the FastMCP gateway (US-0008, PRD-0001). Governed by Hard Invariant 7 (Blackbox TDD with Frontdoor Setup), tests must interact strictly through the public FastMCP protocol entrypoints (`mcp._tool_manager`, `mcp._resource_manager`) as an external client, testing context retrieval and multi-step tool execution.

## Scope & Changes
1. **MCP Resources & Tools (`gateway/mcp/src/gateway_mcp/server.py`)**:
   - Add MCP dynamic resource template `session://{session_id}/state` returning structured JSON of active tokens, encounter threat level, and atmosphere.
   - Add tool `execute_agent_action_plan(session_id: str, actions: list[dict]) -> dict` running multi-turn steps with validation.
   - Maintain file length strictly under 500 lines.
2. **Blackbox TDD Suite (`tests/test_blackbox_mcp_gateway.py`)**:
   - Author blackbox test first using FastMCP client/manager interfaces.
   - Query resource template `session://camp1/state`.
   - Execute multi-step action plan (dice roll, token move, narration).
   - Assert on observable tool output and event publication.
3. **PRD & Backlog Maintenance**:
   - Update `docs/project/product/accepted/prd-0001-the-watcher-ai-dm-and-board-animator.md`.
   - Update `PRIORITY.md` and move card to `complete/`.
