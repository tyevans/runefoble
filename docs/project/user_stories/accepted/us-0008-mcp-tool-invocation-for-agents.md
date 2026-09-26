---
id: 0008
title: MCP Tool Invocation for Autonomous AI Agents
status: Accepted
created: 2026-09-25
persona: Alex (The Developer / Plugin Modder)
feature: FEAT-DEV-01
governing_prd: PRD-0001
---

# US-0008 — MCP Tool Invocation for Autonomous AI Agents

## Governing PRD
- [`PRD-0001: The Watcher AI Dungeon Master and Real-Time Board Animator`](../../product/accepted/prd-0001-the-watcher-ai-dm-and-board-animator.md)

## User Story

**As a** platform developer integrating third-party AI models (e.g. Claude, Gemini, local models),
**I want** Runefoble to expose its tactical board, dice roller, character sheets, and DM controls via the Model Context Protocol (MCP),
**So that** any MCP-compatible agent can inspect session state, make tactical decisions, and act directly in game encounters.

## Scenario: LLM Agent Moves Token via MCP
```gherkin
Given an MCP client connected to gateway/mcp
When the agent invokes the tool "move_board_token" with session_id "sess-001", token_id "t1", to_x 4, to_y 5
Then the MCP gateway returns a structured response confirming the new coordinates
And The Watcher broadcasts a BoardMoveEvent across Redis Streams
And the live board animates the token for all human players.
```
