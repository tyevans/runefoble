---
id: '0119'
title: PRD Decomposer Planning and Slice Generation Modular Decomposition
status: Refined
created: 2026-09-26
dependencies: []
governing_adrs:
- ADR-0003
target_release: 0.3.0
---

# TASK-0119: PRD Decomposer Planning and Slice Generation Modular Decomposition

## Status
Refined

## Summary
Decompose `tools/prd_pipeline/decomposer.py` (432 lines, 86.4% of limit) into an orchestrator facade (`decomposer.py`) and specialized planning and templating modules (`planner.py`, `templates.py`) to prevent violating Hard Invariant 6 (File length limit < 500 lines).

## Problem Statement
`tools/prd_pipeline/decomposer.py` manages all PRD decomposition, vertical slice generation, and markdown templating across 432 lines:
1. Architectural spike heuristics and bounded context resolution (`_requires_architectural_spike`, `_generate_spike_task`).
2. Vertical slice planning and dependency sequencing (`plan_decomposition`, `_generate_slice_tasks`).
3. User story markdown generation and INVEST acceptance criteria formatting (`_generate_story`).
4. Task frontmatter and markdown body rendering with ADR/PRD cross-linking (`_format_task_markdown`).
5. Disk persistence and backlog/story directory writing (`execute_decomposition`).

As new microservice bounded contexts, UI slice archetypes, and story personas are introduced, this file will exceed the 500-line ceiling unless modularized.

## Governing Architecture & ADRs
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean modular package structure within `tools/prd_pipeline/`.

## Detailed Specification & Implementation Plan
1. **Decomposition Planner (`tools/prd_pipeline/planner.py`)**:
   - Spike heuristics, slice typing, and dependency graph assembly (< 120 lines).
2. **Backlog & Story Templating (`tools/prd_pipeline/templates.py`)**:
   - Task draft markdown formatting, story acceptance criteria rendering, and metadata serialization (< 130 lines).
3. **Decomposer Facade (`tools/prd_pipeline/decomposer.py`)**:
   - `PRDDecomposer` class coordinating repo root resolution, invoking planner and template modules, and writing files (< 120 lines).

## INVEST Criteria Evaluation
- **Independent (I)**: Pure internal refactoring of the PRD decomposer tool without altering public class interfaces or generated markdown format.
- **Negotiable (N)**: Split of helper methods between planner and templates.
- **Valuable (V)**: Protects against Hard Invariant 6 violations (< 500 lines) and improves maintainability of backlog automation.
- **Estimable (E)**: Straightforward separation of planning heuristics and string templating.
- **Small (S)**: Scope strictly isolated to `tools/prd_pipeline/`; all resulting files < 150 lines.
- **Testable (T)**: Verified with `tests/test_prd_pipeline.py`.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Decomposition Executed**:
   - `tools/prd_pipeline/decomposer.py` decomposed into `decomposer.py`, `planner.py`, and `templates.py`.
2. **Strict Line Limit**:
   - All modules in `tools/prd_pipeline/` strictly under 200 lines in compliance with Hard Invariant 6.
3. **Full Backward Compatibility**:
   - 100% backward compatibility for `PRDDecomposer` methods (`plan_decomposition`, `execute_decomposition`, `get_max_task_number`, `get_max_story_number`).
4. **Frontdoor Test Verification**:
   - All tests pass via `uv run pytest tests/test_prd_pipeline.py`.
