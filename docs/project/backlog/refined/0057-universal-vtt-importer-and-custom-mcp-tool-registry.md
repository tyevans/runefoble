---
id: '0057'
title: Universal VTT Importer and Dynamic MCP Tool Registry
status: Refined
created: 2026-09-25
dependencies:
- TASK-0005
- TASK-0007
- TASK-0020
- TASK-0023
governing_adrs:
- ADR-0007
- ADR-0008
- ADR-0010
- ADR-0013
target_release: 0.3.0
governing_prds:
- PRD-0009
governing_stories:
- US-0033
- US-0038
---

# TASK-0057: Universal VTT Importer and Dynamic MCP Tool Registry

## Status
Refined

## Summary
Implement a Universal VTT (`.dd2vtt`) map format ingestion parser in `services/board_state` and a dynamic runtime FastMCP tool registration system in `gateway/mcp` enabling community map imports and extensible AI toolsets without gateway restarts.

## Problem Statement
Tabletop modders and third-party creators (Alex) are currently unable to import standard Universal VTT battlemap files containing wall line-of-sight boundaries, door portals, and grid calibrations. Furthermore, exposing custom LLM tools requires modifying code and redeploying the FastMCP gateway, hindering developer extensibility (PRD-0009, US-0033).

## Governing Architecture & ADRs
- **ADR-0007: Real-Time Voice and Board Synchronization**: Wall and obstruction line synchronization across connected clients.
- **ADR-0008: FastMCP Gateway Architecture**: Exposing dynamic tabletop tools and session context resources to LLMs.
- **ADR-0010: Silo S3 Media Storage Pipeline**: Storing parsed `.dd2vtt` background imagery and asset references.
- **ADR-0013: Microfrontend Architecture & Service Component Vendoring**: Integrating import triggers in the board state microfrontend.

## Product & User Story References
- **Product Requirement**: [`prd-0009-procedural-battlemap-and-token-asset-generation.md`](../../product/accepted/prd-0009-procedural-battlemap-and-token-asset-generation.md)
- **User Stories**:
  - [`us-0033-universal-vtt-map-importer-and-scriptable-tiles.md`](../../user_stories/accepted/us-0033-universal-vtt-map-importer-and-scriptable-tiles.md)
  - [`us-0038-generative-procedural-battlemaps-and-tokens.md`](../../user_stories/accepted/us-0038-generative-procedural-battlemaps-and-tokens.md)

## Detailed Specification & Implementation Plan
1. **Universal VTT Format Parser (`services/board_state/src/board_state/parsers/uvtt.py`)**:
   - Parse `.dd2vtt` JSON: extract grid resolution, canvas dimensions, line-of-sight wall vectors, door coordinates, and ambient lights.
   - Extract embedded base64 image data and store background texture into Silo S3 via `services/board_state`.
   - Mutate `BoardStateAggregate` with parsed wall obstacles and grid bounds.
2. **Dynamic FastMCP Tool Registry (`gateway/mcp/src/gateway_mcp/dynamic_registry.py`)**:
   - Provide administrative endpoints to register, update, and deregister runtime FastMCP tool definitions.
   - Validate JSON Schema parameters and execution sandbox policies.
   - Expose updated tools dynamically in `/mcp/tools` listing without dropping existing client SSE connections.
3. **Frontdoor Blackbox Verification**:
   - Create `tests/test_blackbox_uvtt_import.py` verifying file ingestion, wall coordinate projection, and dynamic tool invocation.

## INVEST Criteria Evaluation
- **Independent (I)**: Parser operates strictly on board domain models; tool registry integrates directly into FastMCP server.
- **Negotiable (N)**: Support for complex lighting properties in `.dd2vtt` can be graduated.
- **Valuable (V)**: Opens Runefoble to thousands of community maps exported from Dungeondraft and other standard cartography tools.
- **Estimable (E)**: Standard JSON schema parsing and FastMCP tool wrapper registration.
- **Small (S)**: Scope isolated to parser and tool registration sub-modules; all files < 250 lines.
- **Testable (T)**: Tested via public HTTP file upload endpoints and FastMCP tool calls.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Universal VTT Ingestion API**:
   - `POST /api/v1/board/{id}/import/uvtt` accepts valid `.dd2vtt` files, populates wall segments, and stores map imagery.
2. **FastMCP Dynamic Tool Listing**:
   - Dynamically registered tools appear immediately in FastMCP tool discovery without gateway restarts.
3. **Frontdoor Blackbox Test Suite**:
   - `tests/test_blackbox_uvtt_import.py` asserting wall geometry extraction, board state mutations, and dynamic MCP execution.
4. **Quality Gates**:
   - Conforms strictly to Hard Invariant 6 (< 500 lines per file).
   - Passes `uv run pytest tests/test_blackbox_uvtt_import.py` and `uv run ruff check`.
