---
id: '0187'
title: Campaign Atlas Blackbox Test Suite Modular Decomposition
status: Proposed
created: 2026-09-27
dependencies:
- TASK-0106
governing_adrs:
- ADR-0001
- ADR-0003
- ADR-0007
governing_prds:
- PRD-0015
governing_stories:
- US-0050
target_release: 0.7.0
---

# TASK-0187: Campaign Atlas Blackbox Test Suite Modular Decomposition

## Status
Proposed

## Summary
Decompose `tests/test_blackbox_campaign_atlas.py` (346 lines, 69.2% of limit) into modular focused test suites under `tests/test_blackbox_campaign_atlas/` (`test_territories.py`, `test_pins.py`, `test_codex_links.py`), keeping all test modules strictly < 180 lines per Hard Invariant 6 and Hard Invariant 7.

## Problem Statement
`tests/test_blackbox_campaign_atlas.py` contains 346 lines verifying geopolitical territory definitions, polygon coordinate containment, milestone pin placements, era filtering, and codex cross-links. With shared world frontier additions in Milestone 9, this test suite will expand beyond 400 lines unless decomposed into modular test suites.

## Governing Architecture & ADRs
- **ADR-0001: Zanzibar Fine-Grained Authorization with SpiceDB**: Access control verification on territory and pin access.
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean test module structure across workspace.
- **ADR-0007: Domain-Driven Design Architecture**: Clean domain separation between territory boundaries, atlas pins, and codex lore.

## Scope of Work
1. **Modular Test Package (`tests/test_blackbox_campaign_atlas/`)**:
   - `test_atlas_territories.py`: Geopolitical boundary definitions, polygon containment queries, and contested territory updates (< 140 lines).
   - `test_atlas_pins.py`: Milestone pin placement, pin coordinates, era filtering, and permission checks (< 120 lines).
   - `test_atlas_codex_links.py`: Cross-linking pins to codex entries and shared world metadata (< 100 lines).
2. **Test Shim (`tests/test_blackbox_campaign_atlas.py`)**:
   - Provide backward-compatible test entrypoint or cleanly transition imports.
3. **Verification**:
   - Run `uv run pytest tests/test_blackbox_campaign_atlas/` and verify all tests pass.

## Definition of Done
- `tests/test_blackbox_campaign_atlas.py` decomposed into focused sub-suites under `tests/test_blackbox_campaign_atlas/`.
- All test files strictly < 180 lines.
- All atlas blackbox tests pass via `uv run pytest`.
- Code passes `uv run ruff check .` and `uv run ruff format --check .`.
