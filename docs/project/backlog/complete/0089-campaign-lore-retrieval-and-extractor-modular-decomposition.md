---
id: 0089
title: Campaign Lore Extraction, Embeddings, and Hybrid Retrieval Modular Decomposition
status: Complete
created: 2026-09-26
dependencies:
- TASK-0047
governing_adrs:
- ADR-0003
- ADR-0008
- ADR-0009
target_release: 0.2.0
pr_url: https://github.com/tyevans/runefoble/pull/60
governing_prds:
- PRD-0007
governing_stories:
- US-0036
---
# TASK-0089: Campaign Lore Extraction, Embeddings, and Hybrid Retrieval Modular Decomposition

## Status
Refined

## Summary
Decompose `services/campaign_lore/src/campaign_lore/retrieval.py` (428 lines, 85.6% of limit) into modular submodules (`extraction.py`, `scoring.py`, and `retrieval.py`) to prevent breaching Hard Invariant 6 (File length limit < 500 lines) as worldbuilding NER extraction heuristics and hybrid RAG scoring algorithms expand.

## Problem Statement
`services/campaign_lore/src/campaign_lore/retrieval.py` currently stands at 428 lines—the second largest production service file in the repository—placing it within 72 lines of breaching the 500-line hard invariant ceiling. The module conflates three distinct layers of functionality:
1. LLM-based entity extraction and heuristic Named Entity Recognition (NER), alias pattern matching, and entity typing (`WorldbuildingLlmProvider`, `alias_patterns`, proper noun scanning).
2. Lexical and vector retrieval scoring primitives (BM25 tokenization, term frequency weighting, inverse document frequency calculation, dense vector cosine similarity).
3. The hybrid retrieval engine coordinator (`HybridLoreEngine`, graph neighbor traversal via `redstring`, Reciprocal Rank Fusion / RRF hybrid scoring, alias consolidation queries).

As Milestone 3 deepens lore entity relationships and imports external campaign sourcebooks, this file will rapidly breach Hard Invariant 6 unless decomposed.

## Governing Architecture & ADRs
- **ADR-0003**: UV Monorepo Workspace for Python Bounded Contexts.
- **ADR-0008**: Property and Mutation Testing Strategy.
- **ADR-0009**: Code Quality and Linting with Ruff (strict file length invariant < 500 lines).

## Proposed Decomposition
1. **Worldbuilding Entity & Alias Extraction (`services/campaign_lore/src/campaign_lore/extraction.py`)**:
   - Extract `WorldbuildingLlmProvider`, heuristic NER regexes, entity typing rules, and alias detection patterns (< 150 lines).
2. **Lexical & Vector Scoring Algorithms (`services/campaign_lore/src/campaign_lore/scoring.py`)**:
   - Extract BM25 tokenization, term scoring, cosine similarity, and RRF rank fusion logic (< 130 lines).
3. **Hybrid Retrieval Engine Coordinator (`services/campaign_lore/src/campaign_lore/retrieval.py`)**:
   - Retain `HybridLoreEngine`, query execution, graph neighbor traversal, and public retrieval interfaces (< 190 lines).

## INVEST Criteria Evaluation
- **Independent (I)**: Refactors internal retrieval submodules without modifying `services/campaign_lore` public HTTP endpoints (`/api/v1/lore/query`, `/api/v1/lore/entities`) or domain events.
- **Negotiable (N)**: Split boundaries between BM25 tokenization and vector ranking can be adapted.
- **Valuable (V)**: Protects against Hard Invariant 6 violations (< 500 lines) and enables independent optimization of RAG retrieval algorithms.
- **Estimable (E)**: Pure refactoring separating NER extraction and scoring algorithms from the engine coordinator.
- **Small (S)**: Scope strictly isolated to `services/campaign_lore/src/campaign_lore/`; all resulting files < 200 lines.
- **Testable (T)**: `uv run pytest tests/test_blackbox_campaign_lore_rag.py` verifies 100% identical query results, graph traversal, and alias consolidation.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Modular Submodule Creation**:
   - `services/campaign_lore/src/campaign_lore/extraction.py` and `services/campaign_lore/src/campaign_lore/scoring.py` created.
   - `services/campaign_lore/src/campaign_lore/retrieval.py` refactored as a lean coordinator.
2. **Re-Export Compatibility**:
   - Clean re-exports in `retrieval.py` and `__init__.py` ensure zero breaking changes to existing callers or test fixtures.
3. **File Length Compliance (Hard Invariant 6)**:
   - All modified and new files strictly under 220 lines.
4. **Frontdoor Blackbox Verification**:
   - 100% pass rate on `uv run pytest tests/test_blackbox_campaign_lore_rag.py`.
5. **Quality Gates**:
   - Passes `uv run ruff check services/campaign_lore` and `uv run ruff format --check services/campaign_lore`.
