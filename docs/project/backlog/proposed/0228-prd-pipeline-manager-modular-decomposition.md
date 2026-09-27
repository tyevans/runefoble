---
id: '0228'
title: PRD Pipeline Manager Modular Decomposition
status: Proposed
created: 2026-09-27
dependencies: []
governing_adrs:
- ADR-0003
- ADR-0007
governing_prds: []
governing_stories: []
target_release: 0.8.0
---

# TASK-0228: PRD Pipeline Manager Modular Decomposition

## Status
Proposed

## Summary
Decompose `tools/prd_pipeline/prd_manager.py` (323 lines, 64.6% of limit) into modular Python submodules under `tools/prd_pipeline/manager/` (`models.py`, `scanner.py`, `auditor.py`), ensuring all modules remain strictly < 130 lines per Hard Invariant 6.

## Problem Statement
`tools/prd_pipeline/prd_manager.py` orchestrates PRD scanning across idea/shaped/accepted/shipped stages, requirement checklist auditing, backlog task linking, and status reporting in a monolithic 323-line module. As automated acceptance criteria validation and traceability matrices are expanded, this module will approach the 500-line limit unless decomposed.

## Governing Architecture & ADRs
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean modular tool structure.
- **ADR-0007: Domain-Driven Design Architecture**: Clean domain segregation.

## Scope of Work
1. **Pipeline Models (`tools/prd_pipeline/manager/models.py`)**:
   - Extract `PRDStage`, `PRDRecord`, and `AuditSummary` dataclasses (< 90 lines).
2. **Directory Scanner (`tools/prd_pipeline/manager/scanner.py`)**:
   - Extract stage directory crawling, frontmatter parsing, and story extraction (< 110 lines).
3. **Requirement Auditor (`tools/prd_pipeline/manager/auditor.py`)**:
   - Extract INVEST criteria checking, task linking verification, and gap detection (< 110 lines).
4. **Aggregator Facade (`tools/prd_pipeline/prd_manager.py` or `manager/__init__.py`)**:
   - Re-export `PRDManager` maintaining full API compatibility (< 30 lines).
5. **Verification**:
   - Verify tests pass via `uv run pytest tests/test_prd_pipeline.py`.

## Definition of Done
- Modular `manager/` submodules strictly < 130 lines each.
- Backwards compatibility preserved.
- Passes `uv run pytest tests/test_prd_pipeline.py`.
