---
id: '0496'
title: Remove Backward Compatibility Shims & Re-exports in rules_compendium
status: Refined
created: 2026-09-29
dependencies:
- TASK-0048
- TASK-0350
governing_adrs:
- ADR-0003
- ADR-0009
- ADR-0013
governing_prds:
- PRD-0008
governing_stories:
- US-0008
- US-0029
target_release: 0.9.0
---

# TASK-0496: Remove Backward Compatibility Shims & Re-exports in rules_compendium

## Status
Refined

## Summary
Decommission backward-compatibility re-export shims (`srd_data.py`), remove transitional query accessor facades and legacy dictionary mappings across `rules_compendium`, and migrate all callers directly to authoritative submodules in `rules_compendium.srd.*`.

## Problem Statement
In `services/rules_compendium`:
- `src/rules_compendium/srd_data.py` exists as a re-export shim forwarding canonical SRD data from `rules_compendium.srd.*`.
- Transitional query helper methods and legacy dictionary aliases remain in `services/rules_compendium/src/rules_compendium/dependencies.py` and aggregate handlers.
To comply with the updated DoR, these transitional shims and re-exports must be excised, standardizing all callers on canonical SRD datasets and aggregate handlers.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/how-to/balance-combat-encounters-and-query-compendium.md`: Canonical SRD 5.1 rules retrieval.
  - `docs/reference/ports-and-endpoints.md`: Rules compendium port 8008.
- **Governing Architecture & ADRs**:
  - **ADR-0003: UV Monorepo Workspace**: Monorepo package boundaries.
  - **ADR-0009: Redstring Knowledge Graph & Hybrid RAG**: Hybrid retrieval patterns.
  - **ADR-0013: Frontend Microfrontend Architecture**: Microfrontend separation.

## Product & User Story References
- [`prd-0008-campaign-lore-and-worldbuilding-rag.md`](../../product/accepted/prd-0008-campaign-lore-and-worldbuilding-rag.md)
- [`us-0029-canonical-srd-compendium-lookup.md`](../../user_stories/accepted/us-0029-canonical-srd-compendium-lookup.md)

## Detailed Specification & Implementation Plan
1. **Delete Re-export Shim**:
   - Delete `services/rules_compendium/src/rules_compendium/srd_data.py`.
   - Update all callers to import SRD datasets directly from `rules_compendium.srd.*`.
2. **Remove Transitional Accessors & Aliases**:
   - In `services/rules_compendium/src/rules_compendium/dependencies.py`, remove legacy accessor functions preserved for old router patterns.
   - Standardize compendium aggregate handlers on direct domain event handling without legacy fallback branches.
3. **Clean Up `rules_compendium/__init__.py`**:
   - Audit and prune package root exports, ensuring only authoritative compendium classes are published.
4. **Update Blackbox Test Suites**:
   - Verify all rules compendium tests in `tests/test_rules_compendium*` pass using direct imports.

## INVEST Criteria Evaluation
- **Independent (I)**: Fully self-contained within `services/rules_compendium`.
- **Negotiable (N)**: Clean Python module imports.
- **Valuable (V)**: Streamlines rules compendium package and eliminates redundant data accessor shims.
- **Estimable (E)**: Clearly bounded to `srd_data.py` and dependency accessors.
- **Small (S)**: File changes well under 50 lines.
- **Testable (T)**: Verified via `uv run pytest tests/test_rules_compendium*`.

## Definition of Done
1. `srd_data.py` deleted.
2. Legacy accessor functions in `dependencies.py` removed.
3. All callers across rules compendium and tests updated to canonical submodules.
4. All rules compendium tests pass cleanly.
