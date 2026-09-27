---
id: '0173'
title: Universal VTT Door and Dynamic Lighting Parser
status: Proposed
created: 2026-09-26
dependencies:
- TASK-0057
governing_adrs:
- ADR-0003
- ADR-0006
- ADR-0007
- ADR-0011
governing_prds:
- PRD-0022
governing_stories:
- US-0033
target_release: 0.7.0
---

# TASK-0173: Universal VTT Door and Dynamic Lighting Parser

## Status
Refined

## Summary
Extend the Universal VTT (`.uvtt` / `.dd2vtt`) importer in `services/board_state/` to extract interactive door geometries, secret portal triggers, and point-light sources directly into board state lighting and wall segments.

## Problem Statement
While basic UVTT wall boundary import is functional, doors, secret portals, and light sources are omitted, requiring DMs to manually re-author door states and point-lights on imported maps.

## Governing Architecture & ADRs
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean module layout in `services/board_state/src/board_state/uvtt/`.
- **ADR-0006: Redis Streams Distributed Domain Event Streaming**: Board illumination and door state events.
- **ADR-0007: Domain-Driven Design Architecture**: Clean domain segregation for board spatial geometries and illumination models.
- **ADR-0011: PostgreSQL Event Store via Eventsource-py**: Persist door toggles and dynamic lights on board state aggregate.

## Product & User Story References
- **Product Requirement**: [`prd-0022-extensible-modder-platform-and-mcp-registry.md`](../../product/accepted/prd-0022-extensible-modder-platform-and-mcp-registry.md)
- **User Story**: [`us-0033-universal-vtt-map-importer-and-scriptable-tiles.md`](../../user_stories/accepted/us-0033-universal-vtt-map-importer-and-scriptable-tiles.md)

## Detailed Specification & Implementation Plan
1. **Door & Portal Geometry Extractor (`services/board_state/src/board_state/uvtt/doors.py`)**:
   - Parse door coordinate segments, pivot hinges, open/closed/locked status, and secret detection DCs (< 130 lines).
2. **Point Light & Radiance Mapper (`services/board_state/src/board_state/uvtt/lights.py`)**:
   - Parse UVTT light sources (color hex, bright radius, dim radius, flicker intensity) into board light models (< 120 lines).
3. **CloudEvents Registration (`libs/runefoble_events/src/runefoble_events/uvtt_elements.py`)**:
   - Define `BoardDoorToggledEvent` and `BoardLightSourcePlacedEvent` (< 70 lines).
4. **Board Parser APIRouter (`services/board_state/src/board_state/routers/uvtt_import.py`)**:
   - Extend import endpoint `POST /board/{session_id}/import/uvtt` to populate interactive doors and lights (< 140 lines).

## INVEST Criteria Evaluation
- **Independent (I)**: Supplements existing map import pipeline without breaking static wall occlusion logic.
- **Negotiable (N)**: Default light falloff exponents and secret door detection thresholds are configurable.
- **Valuable (V)**: Drastically reduces DM preparation time when importing community-made Dungeondraft maps.
- **Estimable (E)**: Pure geometric JSON parsing and standard board state entity creation.
- **Small (S)**: Bounded strictly to `services/board_state/src/board_state/uvtt/`; all modules < 150 lines.
- **Testable (T)**: Frontdoor blackbox tests verify 100% geometric extraction and door toggle state machine.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Parser Architecture**:
   - `services/board_state/src/board_state/uvtt/` created with focused submodules.
   - All modules strictly < 160 lines per Hard Invariant 6.
2. **Frontdoor Test Verification**:
   - Blackbox test suite `tests/test_blackbox_uvtt_doors_lights/` asserts door state transitions and light placement over HTTP/WS.
3. **Quality Gates**:
   - Passes `uv run pytest tests/test_blackbox_uvtt_doors_lights/`, `uv run ruff check .`, and `uv run ruff format --check .`.
