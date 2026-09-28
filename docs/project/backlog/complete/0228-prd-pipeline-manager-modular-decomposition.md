---
id: 0228
title: PRD Pipeline Manager Modular Decomposition
status: Complete
created: 2026-09-27
dependencies: []
governing_adrs:
- ADR-0003
- ADR-0007
- ADR-0013
governing_prds: []
governing_stories: []
target_release: 0.8.0
pr_url: https://github.com/tyevans/runefoble/pull/324
---
# TASK-0228: PRD Pipeline Manager Modular Decomposition

## Status
Refined

## Summary
Decompose `tools/prd_pipeline/prd_manager.py` (323 lines, 64.6% of limit) into modular Python submodules under `tools/prd_pipeline/manager/` (`models.py`, `scanner.py`, `auditor.py`), ensuring all modules remain strictly < 130 lines per Hard Invariant 6.

## Problem Statement
`tools/prd_pipeline/prd_manager.py` orchestrates PRD scanning across idea/shaped/accepted/shipped stages, requirement checklist auditing, backlog task linking, and status reporting in a monolithic 323-line module. As automated acceptance criteria validation and traceability matrices are expanded, this module will approach the 500-line limit unless decomposed.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/how-to/decompose-prds-into-vertical-slices.md`: PRD lifecycle, stage directories, and vertical slice decomposition.
  - `docs/how-to/curate-backlog-and-roadmap.md`: Backlog management and requirement linking.
- **Governing Architecture & ADRs**:
  - **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean modular tool structure.
  - **ADR-0007: Domain-Driven Design Architecture**: Clean domain segregation.
  - **ADR-0013: Modular Decomposition**: Single-responsibility Python modules strictly < 150 lines.

## Product & User Story References
- Technical debt refactoring supporting internal developer tooling:
  - [`docs/how-to/decompose-prds-into-vertical-slices.md`](../../../how-to/decompose-prds-into-vertical-slices.md)

## Detailed Specification & Implementation Plan
1. **Pipeline Models (`tools/prd_pipeline/manager/models.py`)**:
   - Extract `PRDStage`, `PRDRecord`, and `AuditSummary` dataclasses (< 90 lines).
2. **Directory Scanner (`tools/prd_pipeline/manager/scanner.py`)**:
   - Extract stage directory crawling, frontmatter parsing, and story extraction (< 110 lines).
3. **Requirement Auditor (`tools/prd_pipeline/manager/auditor.py`)**:
   - Extract INVEST criteria checking, task linking verification, and gap detection (< 110 lines).
4. **Aggregator Facade (`tools/prd_pipeline/prd_manager.py` or `manager/__init__.py`)**:
   - Re-export `PRDManager` maintaining full API compatibility (< 35 lines).
5. **Verification**:
   - Verify tests pass via `uv run pytest tests/test_prd_pipeline.py`.

## INVEST Criteria Evaluation
- **Independent (I)**: Internal module decomposition without breaking CLI interface or model dataclasses.
- **Negotiable (N)**: Submodule naming can be tailored.
- **Valuable (V)**: Protects PRD pipeline manager from breaching the 500-line invariant limit.
- **Estimable (E)**: Pure extraction into scanner, auditor, and models.
- **Small (S)**: Submodules will each be strictly < 130 lines.
- **Testable (T)**: Existing test suite verifies scanning, auditing, and report formatting.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. `tools/prd_pipeline/prd_manager.py` facade reduced to < 40 lines.
2. Modular `manager/` submodules strictly < 130 lines each.
3. Backwards compatibility preserved.
4. Passes `uv run pytest tests/test_prd_pipeline.py`.
5. Code passes `uv run ruff check .` and `uv run ruff format --check .`.
