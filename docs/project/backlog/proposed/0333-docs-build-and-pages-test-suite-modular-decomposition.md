---
id: '0333'
title: Docs Build and Pages Test Suite Modular Decomposition
status: Proposed
created: 2026-09-28
dependencies:
- TASK-0028
governing_adrs:
- ADR-0013
governing_prds:
- PRD-0013
governing_stories:
- US-0043
target_release: 0.8.0
---

# TASK-0333: Docs Build and Pages Test Suite Modular Decomposition

## Status
Proposed

## Summary
Decompose `tests/test_docs_build_and_pages.py` (267 lines, 53.4% of limit) into modular sub-suites under `tests/docs_pages/` (`test_zensical_config.py`, `test_docs_site_generation.py`, and `test_pages_workflow.py`) with an aggregator entry point, keeping all test files strictly < 100 lines per Hard Invariant 6.

## Problem Statement
`tests/test_docs_build_and_pages.py` tests Zensical configuration, documentation navigation targets, site generation, visualizer HTML artifact embedding, and GitHub Pages workflow definitions in a single test module. As new documentation sections, ADRs, and deployment checks are added, this test suite will approach the 500-line limit unless decomposed into focused modules.

## Governing Architecture & ADRs
- **ADR-0013: Modular Decomposition**: All source and test files kept strictly < 500 lines (sub-suites < 100 lines).

## Scope of Work
1. **Zensical Configuration Tests (`tests/docs_pages/test_zensical_config.py`)**:
   - Extract `test_zensical_configuration` navigation link verification and config validations (< 80 lines).
2. **Site Generation & Visualizer Tests (`tests/docs_pages/test_docs_site_generation.py`)**:
   - Extract `test_docs_site_generation_and_visualizer_integration` HTML asset and visualizer verification (< 95 lines).
3. **Workflow & Deployment Tests (`tests/docs_pages/test_pages_workflow.py`)**:
   - Extract `test_github_pages_deployment_workflow` and CI configuration checks (< 85 lines).
4. **Aggregator Entry Point (`tests/test_docs_build_and_pages.py`)**:
   - Re-export test cases to preserve pytest discovery compatibility (< 25 lines).

## Definition of Done
- `test_docs_build_and_pages.py` decomposed into modular sub-suites under `tests/docs_pages/`.
- All created and modified files strictly < 100 lines each per Hard Invariant 6.
- `pytest tests/test_docs_build_and_pages.py` executes all checks with 100% pass rate.
