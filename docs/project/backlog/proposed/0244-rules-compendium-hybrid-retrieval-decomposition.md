---
id: '0244'
title: Rules Compendium Hybrid Retrieval Modular Decomposition
status: Proposed
created: 2026-09-27
dependencies:
- TASK-0048
governing_adrs:
- ADR-0003
- ADR-0007
governing_prds:
- PRD-0008
governing_stories:
- US-0037
- US-0052
target_release: 0.7.0
---

# TASK-0244: Rules Compendium Hybrid Retrieval Modular Decomposition

## Status
Proposed

## Summary
Decompose `services/rules_compendium/src/rules_compendium/retrieval.py` (306 lines, 61.2% of limit) into modular submodules under `services/rules_compendium/src/rules_compendium/retrieval/` (`bm25.py`, `semantic.py`, `fusion.py`, and `engine.py`), keeping all submodules strictly < 120 lines per Hard Invariant 6 and ADR-0003.

## Problem Statement
`services/rules_compendium/src/rules_compendium/retrieval.py` contains 306 lines combining redstring BM25 lexical token matching, semantic vector embedding projection, reciprocal rank fusion (RRF) scoring, and compendium query execution across canonical SRD items and custom homebrew rules. As spell slot level filters, monster CR ranges, and condition index lookups expand, this file will breach the 400-line warning threshold unless decoupled.

## Governing Architecture & ADRs
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean internal package layout for microservice bounded contexts.
- **ADR-0007: Domain-Driven Design Architecture**: Clean domain segregation between BM25 lexical ranking, semantic vector projection, and hybrid ranking fusion.

## Scope of Work
1. **BM25 Lexical Submodule (`services/rules_compendium/src/rules_compendium/retrieval/bm25.py`)**:
   - Extract lexical token indexing, BM25 query construction, and exact rule name matching (< 90 lines).
2. **Semantic Vector Submodule (`services/rules_compendium/src/rules_compendium/retrieval/semantic.py`)**:
   - Extract semantic embedding projection and vector similarity calculations (< 90 lines).
3. **Reciprocal Rank Fusion Submodule (`services/rules_compendium/src/rules_compendium/retrieval/fusion.py`)**:
   - Extract rank fusion scoring, deduplication, and score thresholding routines (< 90 lines).
4. **Retrieval Engine Facade (`services/rules_compendium/src/rules_compendium/retrieval/engine.py` / `__init__.py`)**:
   - Maintain `CompendiumRetrievalEngine` wiring together lexical and semantic pipelines with backward-compatible exports (< 80 lines).
5. **Verification**:
   - Verify blackbox tests in `tests/test_blackbox_rules_compendium.py`.

## Definition of Done
- `services/rules_compendium/src/rules_compendium/retrieval/` created with all submodules strictly < 120 lines each.
- `services/rules_compendium/src/rules_compendium/retrieval.py` replaced by the modular package with full backward compatibility.
- All rules compendium tests pass via `uv run pytest tests/test_blackbox_rules_compendium.py`.
- Formatted and linted cleanly via `uv run ruff check .` and `uv run ruff format --check .`.
