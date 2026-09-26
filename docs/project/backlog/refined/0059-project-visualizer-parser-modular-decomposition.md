---
id: '0059'
title: Project Visualizer Parser Modular Decomposition
status: Refined
created: 2026-09-26
dependencies: []
governing_adrs:
- ADR-0003
target_release: 0.2.0
---

# TASK-0059: Project Visualizer Parser Modular Decomposition

## Status
Refined

## Summary
Decompose `tools/project_visualizer/parser.py` (461 lines, 92.2% of limit) into modular, single-responsibility sub-parsers (`adr_parser.py`, `backlog_parser.py`, `product_parser.py`, `graph_builder.py`) to prevent violating Hard Invariant 6 (File length limit < 500 lines).

## Problem Statement
`tools/project_visualizer/parser.py` currently spans 461 lines. It acts as a monolithic parser responsible for:
1. Markdown frontmatter extraction and section heading parsing (`parse_frontmatter`, `extract_section`, `extract_list_items`).
2. Architecture Decision Record (ADR) file scanning and status classification (`parse_adr_files`).
3. Product Requirements Documents (PRDs) and user story scanning (`parse_prd_files`, `parse_user_story_files`).
4. Engineering backlog parsing across complete, refined, and proposed directories (`parse_backlog_files`).
5. Roadmap milestone parsing (`parse_roadmap_file`).
6. Cross-entity dependency and traceability matrix graph building (`build_traceability_graph`, `scan_project`).

As new metadata fields, personas, and trace links are added to the documentation schema, this file will breach the 500-line hard invariant ceiling.

## Governing Architecture & ADRs
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean module layout and packaging within `tools/project_visualizer/`.

## Detailed Specification & Implementation Plan
1. **Sub-Parsers Package (`tools/project_visualizer/parsers/`)**:
   - `markdown_utils.py`: Shared frontmatter, section extraction, and list item utilities (< 80 lines).
   - `adr_parser.py`: ADR scanning, status extraction, and decision record models (< 80 lines).
   - `product_parser.py`: PRD status lifecycle and persona-driven user story parsers (< 110 lines).
   - `backlog_parser.py`: Backlog tasks, priority ranking, and roadmap milestone extraction (< 110 lines).
   - `graph_builder.py`: Traceability matrix, dependency linking, and graph model population (< 120 lines).
2. **Facade & Entrypoint (`tools/project_visualizer/parser.py`)**:
   - Retain `scan_project` and core parser functions as clean facades re-exporting from `parsers/` (< 90 lines).
   - Ensure backward compatibility with existing tests (`tests/test_project_visualizer.py`) and scripts (`scripts/generate_project_graph.py`).

## INVEST Criteria Evaluation
- **Independent (I)**: Refactors internal tool parsing structure without altering data models, CLI interfaces, or exported JSON schemas.
- **Negotiable (N)**: File boundaries between product and backlog parsers can be adjusted.
- **Valuable (V)**: Protects against Hard Invariant 6 violations (< 500 lines) in repository developer tooling and enhances readability.
- **Estimable (E)**: Pure extraction of discrete parsing functions into focused modules.
- **Small (S)**: Scope strictly isolated to `tools/project_visualizer/`; all resulting files will be < 150 lines.
- **Testable (T)**: `pytest tests/test_project_visualizer.py` and `python3 scripts/generate_project_graph.py` verify identical parsed JSON output and graph structure.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Decomposition Executed**:
   - `tools/project_visualizer/parser.py` decomposed into `parser.py` and dedicated sub-parsers in `tools/project_visualizer/parsers/`.
2. **Strict Line Limit**:
   - All modules in `tools/project_visualizer/` strictly under 200 lines in compliance with Hard Invariant 6.
3. **Full Backward Compatibility**:
   - 100% backward compatibility for all public functions on `tools.project_visualizer.parser` (`scan_project`, `parse_frontmatter`, etc.).
4. **Frontdoor Test Verification**:
   - All tests pass via `uv run pytest tests/test_project_visualizer.py`.
