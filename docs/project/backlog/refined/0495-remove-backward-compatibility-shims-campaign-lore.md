---
id: '0495'
title: Remove Backward Compatibility Shims & Re-exports in campaign_lore
status: Refined
created: 2026-09-29
dependencies:
- TASK-0047
- TASK-0349
governing_adrs:
- ADR-0003
- ADR-0009
- ADR-0013
governing_prds:
- PRD-0008
governing_stories:
- US-0008
- US-0028
target_release: 0.9.0
---

# TASK-0495: Remove Backward Compatibility Shims & Re-exports in campaign_lore

## Status
Refined

## Summary
Decommission backward-compatibility router facades (`services/campaign_lore/src/campaign_lore/routers/codex.py`), excise class aliases in `retrieval.py` (`HybridRetrieval = HybridRetrievalCoordinator`), clean up package-root re-exports, and remove backward-compatibility tests in `tests/test_campaign_lore_modular_retrieval.py`.

## Problem Statement
In `services/campaign_lore`:
- `src/campaign_lore/routers/codex.py` is a 37-line facade explicitly documented as `"""Facade backward compatibility re-exporting modular codex router and schemas."""`
- `src/campaign_lore/retrieval.py` retains `# Backward-compatibility alias as defined in architecture records` (`HybridRetrieval = HybridRetrievalCoordinator`).
- `tests/test_campaign_lore_modular_retrieval.py:test_import_from_retrieval_backward_compatibility` actively asserts that `campaign_lore.retrieval preserves 100% backward compatibility`.
Retaining these shims introduces dual import paths and violates the DoR zero backward compatibility mandate.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/how-to/index-campaign-lore-with-redstring.md`: Worldbuilding document indexing and hybrid retrieval.
  - `docs/how-to/interact-with-campaign-atlas-and-codex.md`: Campaign codex and lore notes.
- **Governing Architecture & ADRs**:
  - **ADR-0009: Redstring Knowledge Graph & Hybrid RAG**: Worldbuilding knowledge graphs.
  - **ADR-0013: Frontend Microfrontend Architecture**: Microfrontend component vendoring.

## Product & User Story References
- [`prd-0008-campaign-lore-and-worldbuilding-rag.md`](../../product/accepted/prd-0008-campaign-lore-and-worldbuilding-rag.md)
- [`us-0008-worldbuilding-lore-document-indexing.md`](../../user_stories/accepted/us-0008-worldbuilding-lore-document-indexing.md)
- [`us-0028-campaign-codex-and-knowledge-graph-retrieval.md`](../../user_stories/accepted/us-0028-campaign-codex-and-knowledge-graph-retrieval.md)

## Detailed Specification & Implementation Plan
1. **Decommission Codex Router Facade**:
   - Delete `services/campaign_lore/src/campaign_lore/routers/codex.py`.
   - Update `campaign_lore/main.py` and router mounts to include modular sub-routers (`routers/codex_entries.py`, `routers/codex_notes.py`) directly.
2. **Remove Class and Module Aliases**:
   - In `services/campaign_lore/src/campaign_lore/retrieval.py`, remove `HybridRetrieval = HybridRetrievalCoordinator` alias.
   - Update any callers to reference `HybridRetrievalCoordinator` directly.
3. **Clean Up `campaign_lore/__init__.py`**:
   - Remove legacy re-export aliases, ensuring only authoritative domain aggregates and services are exposed.
4. **Update Blackbox Test Suites**:
   - In `tests/test_campaign_lore_modular_retrieval.py`, remove `test_import_from_retrieval_backward_compatibility()`.
   - Ensure all campaign lore tests verify behavior through canonical modular interfaces.

## INVEST Criteria Evaluation
- **Independent (I)**: Isolated cleanly to `services/campaign_lore` and its test suites.
- **Negotiable (N)**: Clean modular direct imports following established project conventions.
- **Valuable (V)**: Eliminates 1 facade router and redundant class alias.
- **Estimable (E)**: Clearly identified files (`routers/codex.py`, `retrieval.py`, test file).
- **Small (S)**: File changes conform strictly to < 500 lines per file.
- **Testable (T)**: Verified via `uv run pytest tests/test_campaign_lore*`.

## Definition of Done
1. `routers/codex.py` facade deleted.
2. `HybridRetrieval` alias removed from `retrieval.py`.
3. All internal and external callers migrated to canonical imports.
4. Backward-compatibility tests removed from `tests/test_campaign_lore_modular_retrieval.py`.
5. All campaign lore tests pass cleanly.
