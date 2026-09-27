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
- ADR-0006
- ADR-0007
governing_prds:
- PRD-0022
governing_stories:
- US-0008
- US-0035
target_release: 0.7.0
---

# TASK-0172: Dynamic FastMCP Tool Hot-Reloading Registry

## Status
Refined

## Summary
Implement a dynamic runtime tool registry in `services/gateway_mcp/` allowing developers and game masters to register, update, and hot-reload custom FastMCP tools and prompts at runtime with SpiceDB authorization checks, without restarting the MCP server.

## Problem Statement
Adding or updating community-authored MCP tools currently requires restarting the MCP gateway process, terminating active AI agent sessions and interrupting live game turns.

## Governing Architecture & ADRs
- **ADR-0001: Zanzibar Fine-Grained Authorization with SpiceDB**: Tool registration permissions and scoped execution checks.
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean module layout in `gateway/mcp/src/gateway_mcp/dynamic/`.
- **ADR-0006: Redis Streams Distributed Domain Event Streaming**: Tool lifecycle notifications to `runefoble:events:system`.
- **ADR-0007: Domain-Driven Design Architecture**: Clean domain segregation for runtime tool schemas and execution contexts.

## Product & User Story References
- **Product Requirement**: [`prd-0022-extensible-modder-platform-and-mcp-registry.md`](../../product/accepted/prd-0022-extensible-modder-platform-and-mcp-registry.md)
- **User Story**: [`us-0008-mcp-tool-invocation-for-agents.md`](../../user_stories/accepted/us-0008-mcp-tool-invocation-for-agents.md)
- **User Story**: [`us-0035-runtime-mcp-tool-hot-reloading-and-extension-slots.md`](../../user_stories/accepted/us-0035-runtime-mcp-tool-hot-reloading-and-extension-slots.md)

## Detailed Specification & Implementation Plan
1. **Dynamic Tool Registry State (`gateway/mcp/src/gateway_mcp/dynamic/registry.py`)**:
   - Thread-safe registry mapping tool names to callable async functions with JSON Schema validation (< 140 lines).
2. **SpiceDB Tool Execution Guard (`gateway/mcp/src/gateway_mcp/dynamic/auth.py`)**:
   - Permission verification ensuring only authorized users/agents can register or invoke sensitive tools (< 110 lines).
3. **CloudEvents Registration (`libs/runefoble_events/src/runefoble_events/mcp_tools.py`)**:
   - Define `DynamicToolRegisteredEvent`, `DynamicToolUnregisteredEvent`, and `DynamicToolInvokedEvent` (< 80 lines).
4. **Tool Management REST Router (`gateway/mcp/src/gateway_mcp/routers/tools_registry.py`)**:
   - `POST /mcp/tools/register`: Register a dynamic tool definition at runtime.
   - `DELETE /mcp/tools/{tool_name}`: Unregister an active dynamic tool.
   - `GET /mcp/tools/dynamic`: List active runtime tools (< 130 lines).

## INVEST Criteria Evaluation
- **Independent (I)**: Modulates tool availability without altering underlying FastMCP core protocol handling.
- **Negotiable (N)**: Dynamic registration timeouts and execution sandboxing limits can be configured.
- **Valuable (V)**: Allows instant modding, community tool injection, and custom campaign actions without server downtime.
- **Estimable (E)**: Standard in-memory dictionary registry with JSON schema validation and FastMCP tool decoration.
- **Small (S)**: Bounded strictly to `gateway/mcp/src/gateway_mcp/dynamic/`; all modules < 150 lines.
- **Testable (T)**: Frontdoor blackbox tests verify registration, listing via `tools/list`, and hot unregistration.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Registry Architecture**:
   - `gateway/mcp/src/gateway_mcp/dynamic/` created with focused submodules.
   - All modules strictly < 160 lines per Hard Invariant 6.
2. **Frontdoor Test Verification**:
   - Blackbox test suite `tests/test_blackbox_dynamic_mcp/` verifies hot registration, schema reflection, and invocation.
3. **Quality Gates**:
   - Passes `uv run pytest tests/test_blackbox_dynamic_mcp/`, `uv run ruff check .`, and `uv run ruff format --check .`.
