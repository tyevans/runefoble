---
id: '0489'
title: Remove Backward Compatibility Shims & Re-exports in gateway_mcp
status: Refined
created: 2026-09-29
dependencies:
- TASK-0005
- TASK-0020
governing_adrs:
- ADR-0003
- ADR-0008
governing_prds:
- PRD-0001
governing_stories:
- US-0010
target_release: 0.9.0
---

# TASK-0489: Remove Backward Compatibility Shims & Re-exports in gateway_mcp

## Status
Refined

## Summary
Remove `dynamic_registry.py` backward-compatibility re-exports and legacy tool registry aliases from `gateway/mcp`, routing all MCP tool registrations and inspections directly to authoritative submodules in `gateway_mcp.dynamic.*`.

## Problem Statement
`gateway/mcp/src/gateway_mcp/dynamic_registry.py` exists as a backward-compatibility re-export module forwarding imports to `gateway_mcp.dynamic.*`. In a greenfield platform without external clients, retaining transitional re-export files creates confusion about canonical entry points for FastMCP tool registration and violates DoR rule 9.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/reference/fastmcp-gateway.md`: FastMCP gateway server, tools, and dynamic registry.
  - `docs/how-to/add-a-watcher-ai-tool.md`: Registering FastMCP tools.
- **Governing Architecture & ADRs**:
  - **ADR-0003: UV Monorepo Workspace**: Package separation and modularity.
  - **ADR-0008: FastMCP Gateway for AI Model Tabletop Tools**: Tool lifecycle and execution.

## Product & User Story References
- [`prd-0001-runefoble-platform-foundations.md`](../../product/accepted/prd-0001-runefoble-platform-foundations.md)
- [`us-0010-developer-local-infrastructure-and-test-tooling.md`](../../user_stories/accepted/us-0010-developer-local-infrastructure-and-test-tooling.md)

## Detailed Specification & Implementation Plan
1. **Delete Backward-Compatibility Re-export Module**:
   - Delete `gateway/mcp/src/gateway_mcp/dynamic_registry.py`.
2. **Standardize Imports on `gateway_mcp.dynamic`**:
   - Audit `gateway/mcp/src/gateway_mcp/server.py`, `routers/tools_registry.py`, and test files.
   - Ensure all references to `dynamic_registry` are rewritten to `gateway_mcp.dynamic.registry` (or canonical submodules).
3. **Clean Up `gateway_mcp/__init__.py`**:
   - Verify `__init__.py` exposes only authoritative FastMCP server constructs and zero legacy alias redirects.
4. **Update Blackbox Test Suites**:
   - Verify tests in `tests/test_fastmcp*.py` interact with dynamic tool loading directly through canonical entry points.

## INVEST Criteria Evaluation
- **Independent (I)**: Fully self-contained within `gateway/mcp`.
- **Negotiable (N)**: Clean standard Python module organization.
- **Valuable (V)**: Streamlines FastMCP architecture and removes dead re-export modules.
- **Estimable (E)**: Single file deletion and straightforward import updates.
- **Small (S)**: Confined to 1 file deletion and a few import rewrites.
- **Testable (T)**: Verified via `uv run pytest tests/test_fastmcp*.py`.

## Definition of Done
1. `gateway/mcp/src/gateway_mcp/dynamic_registry.py` deleted.
2. All tool registration call sites migrated to `gateway_mcp.dynamic.*`.
3. Zero backward-compatibility re-exports remain in `gateway/mcp`.
4. FastMCP tool test suites pass cleanly.
5. Code passes `make lint`.
