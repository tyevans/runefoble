---
id: '0472'
title: FastMCP Live Session Transcripts and Initiative Streaming Resources
status: Proposed
created: 2026-09-29
dependencies:
- TASK-0005
- TASK-0020
- TASK-0022
- TASK-0041
governing_adrs:
- ADR-0008
- ADR-0009
governing_prds:
- PRD-0001
- PRD-0022
governing_stories:
- US-0008
target_release: 0.9.0
---

# TASK-0472: FastMCP Live Session Transcripts and Initiative Streaming Resources

## Status
Proposed

## Summary
Expand `gateway/mcp/src/gateway_mcp/resources/session.py` to expose real-time Model Context Protocol (FastMCP) streaming resource endpoints for live session spoken transcripts (`session://{session_id}/transcript`) and active combat turn order / initiative tracking (`session://{session_id}/initiative`). Enable external autonomous AI agents, spectator summarizers, and third-party tools to inspect streaming dialogue history and combat turn queues via standard MCP resource subscriptions.

## Problem Statement
PRD-0022 states that the standardized FastMCP gateway must expose "comprehensive MCP resource endpoints streaming live session transcripts and initiative states." Currently, `gateway/mcp/src/gateway_mcp/resources/session.py` only exposes basic board token coordinates and overall encounter state (`session://{session_id}/state` and `encounter://current`). External LLM agents and tabletop tools cannot read chronological speech transcripts or track initiative turn countdowns through MCP resources, forcing agents to rely on incomplete snapshots or custom HTTP polling.

## Governing Architecture & ADRs
- **ADR-0008: FastMCP Gateway Architecture**: Exposing tabletop context resources to external AI models and developer tools.
- **ADR-0009: Model Context Protocol Integration**: Implementing standardized MCP Resource templates with typed JSON payloads.

## Product & User Story References
- [`prd-0001-the-watcher-ai-dm-and-board-animator.md`](../../product/accepted/prd-0001-the-watcher-ai-dm-and-board-animator.md)
- [`prd-0022-extensible-modder-platform-and-mcp-registry.md`](../../product/accepted/prd-0022-extensible-modder-platform-and-mcp-registry.md)
- [`us-0008-mcp-tool-invocation-for-agents.md`](../../user_stories/accepted/us-0008-mcp-tool-invocation-for-agents.md)

## Scope of Work
1. **Transcript Resource Implementation (`gateway/mcp/src/gateway_mcp/resources/transcript.py`)**:
   - Implement `get_session_transcript(session_id: str, limit: int = 50)` fetching chronological speech-to-intent transcript entries, speaker names, timestamps, and recognized game intents.
   - Register FastMCP resource `session://{session_id}/transcript` (< 120 lines).
2. **Initiative & Turn Order Resource (`gateway/mcp/src/gateway_mcp/resources/initiative.py`)**:
   - Implement `get_session_initiative(session_id: str)` querying `game_session` combat tracker for current round, turn index, active creature ID, initiative order with DEX modifiers, and round timer status.
   - Register FastMCP resource `session://{session_id}/initiative` (< 120 lines).
3. **Resource Aggregator Registration (`gateway/mcp/src/gateway_mcp/resources/__init__.py`)**:
   - Wire transcript and initiative resources into FastMCP server bootstrap alongside existing session resources.
4. **Unit & FastMCP Integration Tests (`gateway/mcp/tests/test_resources_streaming.py`)**:
   - Assert MCP resource resolution for `session://sess-001/transcript` and `session://sess-001/initiative`.

## Definition of Done
1. FastMCP server exposes `session://{session_id}/transcript` returning structured transcript turns.
2. FastMCP server exposes `session://{session_id}/initiative` returning combat turn order and active combatant.
3. All resource modules remain strictly < 130 lines per Hard Invariant 6.
4. Unit tests pass with `uv run pytest gateway/mcp/tests/`.
5. Passes `uv run ruff check .` and `uv run ruff format --check .`.
