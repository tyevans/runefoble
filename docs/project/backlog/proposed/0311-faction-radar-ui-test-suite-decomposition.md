---
id: '0311'
title: Faction Radar UI Test Suite Modular Decomposition
status: Proposed
created: 2026-09-28
dependencies:
- TASK-0137
governing_adrs:
- ADR-0003
- ADR-0007
- ADR-0013
governing_prds:
- PRD-0017
governing_stories:
- US-0057
target_release: 0.8.0
---

# TASK-0311: Faction Radar UI Test Suite Modular Decomposition

## Status
Proposed

## Summary
Decompose `tests/test_blackbox_faction_radar_ui.py` (292 lines, 58.4% of limit) into modular test sub-modules under `tests/test_blackbox_faction_radar_ui/` (`conftest.py`, `test_manifest.py`, `test_radar_rendering.py`, `test_bulletin_drawer.py`), keeping each test module strictly < 150 lines per Hard Invariant 6.

## Problem Statement
`tests/test_blackbox_faction_radar_ui.py` tests manifest registration, SVG radar rendering, tension indicator nodes, and the intelligence bulletin drawer in a single 292-line file. Decomposing it into focused submodules ensures strict adherence to Hard Invariant 6 and prevents file bloat as new faction visualizers are added.

## Governing Architecture & ADRs
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean test suite organization.
- **ADR-0007: Domain-Driven Design Architecture**: Blackbox domain verification.
- **ADR-0013: Modular Decomposition**: All test files kept strictly < 500 lines (submodules < 150 lines).

## Scope of Work
1. **Test Fixtures (`tests/test_blackbox_faction_radar_ui/conftest.py`)**:
   - Shared client fixtures and mock data (< 50 lines).
2. **Manifest & Component Registration (`tests/test_blackbox_faction_radar_ui/test_manifest.py`)**:
   - Verify microfrontend manifest and file invariant checks (< 60 lines).
3. **Radar Rendering & SVG Tests (`tests/test_blackbox_faction_radar_ui/test_radar_rendering.py`)**:
   - Verify polar coordinates, tension rings, and faction icon placement (< 100 lines).
4. **Bulletin Drawer & Intelligence Feed Tests (`tests/test_blackbox_faction_radar_ui/test_bulletin_drawer.py`)**:
   - Verify intelligence briefs, clandestine alerts, and alert severity filtering (< 100 lines).
5. **Verification**:
   - Run `uv run pytest tests/test_blackbox_faction_radar_ui/` to confirm all tests pass.

## Definition of Done
- `tests/test_blackbox_faction_radar_ui.py` migrated to `tests/test_blackbox_faction_radar_ui/` package.
- All extracted test modules strictly < 150 lines each per Hard Invariant 6.
- 100% test coverage preserved with all existing test cases passing cleanly.
