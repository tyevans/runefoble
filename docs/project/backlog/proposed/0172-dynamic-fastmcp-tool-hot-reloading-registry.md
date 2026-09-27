---
id: '0172'
title: Dynamic FastMCP Tool Hot-Reloading Registry
status: Proposed
created: 2026-09-26
dependencies:
- TASK-0041
- TASK-0057
governing_adrs:
- ADR-0001
- ADR-0003
governing_prds:
- PRD-0022
governing_stories:
- US-0008
- US-0035
target_release: 0.7.0
---

# TASK-0172: Dynamic FastMCP Tool Hot-Reloading Registry

## Status
Proposed

## Summary
Implement an in-memory dynamic tool registry in `services/gateway_mcp/` allowing developers to register, update, and hot-reload custom FastMCP tools and prompts at runtime with SpiceDB authorization checks.

## Problem Statement
Adding or updating community-authored MCP tools requires restarting the MCP gateway service, disrupting active AI agent sessions and connected client connections.

## Governing Architecture & ADRs
- **ADR-0001: Zanzibar Fine-Grained Authorization with SpiceDB**: Permission-scoped tool execution.
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Dedicated registry module in `gateway_mcp`.

## Scope of Work
1. **Dynamic Tool Registry State**:
   - Thread-safe registry mapping tool names to callable async functions with JSON Schema validation.
2. **Runtime Hot-Reload REST / Socket Endpoint**:
   - Admin-authenticated route to register or unregister tools on the fly without server interruption.
3. **Frontdoor Verification**:
   - Blackbox tests validating dynamic tool registration, schema reflection, and SpiceDB permission enforcement.

## Definition of Done
- Registry implemented in `services/gateway_mcp/src/gateway_mcp/`.
- Hot-reloaded tools immediately appear in `tools/list` MCP responses.
- Test suite passes via `uv run pytest`.
- File length remains under 250 lines.
