---
id: '0313'
title: Visualizer Parser Test Suite Modular Decomposition
status: Proposed
created: 2026-09-28
dependencies:
- TASK-0224
- TASK-0228
governing_adrs:
- ADR-0003
- ADR-0007
- ADR-0013
governing_prds: []
governing_stories: []
target_release: 0.8.0
---

# TASK-0313: Visualizer Parser Test Suite Modular Decomposition

## Status
Proposed

## Summary
Decompose `tests/test_visualizer_parser.py` (296 lines, 59.2% of limit) into modular test sub-suites under `tests/test_visualizer_parser/` (`conftest.py`, `test_entity_extraction.py`, `test_markdown_utils.py`, `test_metadata_and_subparsers.py`), keeping each test module strictly < 120 lines per Hard Invariant 6.

## Problem Statement
`tests/test_visualizer_parser.py` covers Project Visualizer entity extraction, markdown utility regexes, frontmatter decoding, and individual ADR/PRD/Story/Backlog subparsers in a single 296-line file. As new entities (personas, visualizer graph metrics, interactive roadmap models) are added to the visualization tooling, this test suite will rapidly breach the 500-line ceiling unless partitioned into focused sub-suites.

## Governing Architecture & ADRs
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean modular test structure.
- **ADR-0007: Domain-Driven Design Architecture**: Domain segregation in developer tooling.
- **ADR-0013: Modular Decomposition**: All test files kept strictly < 500 lines (submodules < 120 lines).

## Scope of Work
1. **Fixtures & Test Config (`tests/test_visualizer_parser/conftest.py`)**:
   - Shared repo root fixture and test mock generators (< 40 lines).
2. **Entity Extraction Suite (`tests/test_visualizer_parser/test_entity_extraction.py`)**:
   - Blackbox entity scanning and schema validation tests (< 100 lines).
3. **Markdown Utils Suite (`tests/test_visualizer_parser/test_markdown_utils.py`)**:
   - Prefix extraction, section slicing, list item parsing tests (< 90 lines).
4. **Subparsers & Git Metadata (`tests/test_visualizer_parser/test_metadata_and_subparsers.py`)**:
   - ADR/Product/Backlog subparser tests and Git metadata harvesting (< 100 lines).
5. **Verification**:
   - Run `uv run pytest tests/test_visualizer_parser/` to confirm 100% parity.

## Definition of Done
- `tests/test_visualizer_parser.py` decomposed into `tests/test_visualizer_parser/` package.
- All extracted test modules strictly < 120 lines each.
- 100% test pass rate preserved without regressions.
