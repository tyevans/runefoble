---
id: '0092'
title: Asset Forge Blackbox Test Suite Modular Decomposition
status: Refined
created: 2026-09-26
dependencies:
- TASK-0049
governing_adrs:
- ADR-0003
- ADR-0005
- ADR-0006
- ADR-0009
- ADR-0011
- ADR-0013
target_release: 0.3.0
---

# TASK-0092: Asset Forge Blackbox Test Suite Modular Decomposition

## Status
Refined

## Summary
Decompose `tests/test_blackbox_asset_forge.py` (421 lines, 84.2% of limit) into two specialized blackbox test suites (`tests/test_blackbox_asset_forge_generation.py` and `tests/test_blackbox_asset_forge_auth_and_events.py`) to prevent breaching Hard Invariant 6 (File length limit < 500 lines) as new asset generation modalities are added.

## Problem Statement
`tests/test_blackbox_asset_forge.py` currently spans 421 lines and tests multiple decoupled capabilities of the `asset_forge` service:
1. Procedural battlemap and token generation, Silo S3 binary payload storage, dimensions, transparency, and spatial wall geometry extraction (`test_blackbox_forge_battlemap_generation_and_storage`, `test_blackbox_forge_token_portrait_and_transparency`).
2. CloudEvents schema compliance and Redis Streams event bus publishing (`BattlemapForged`, `TokenAssetForged`), SpiceDB Zanzibar authorization checks (`dungeon_master` role requirement), metadata query endpoints, and input validation rejections.

As image style customization, soundscape triggers, and token animation frames are added in Milestone 3, this test suite will rapidly breach the 500-line hard invariant unless decomposed into focused, single-responsibility suites.

## Governing Architecture & ADRs
- **ADR-0003**: UV Monorepo Workspace for Python Bounded Contexts.
- **ADR-0005**: Kubernetes-First Infrastructure with Helm and Kind.
- **ADR-0006**: Redis Streams Event Bus Transport.
- **ADR-0009**: Continuous Backlog Refinement and Technical Debt Management.
- **ADR-0011**: eventsource-py Core Event Sourcing.
- **ADR-0013**: Microfrontend Architecture and Service Component Vendoring.

## Proposed Decomposition
1. **Procedural Generation & Storage Suite (`tests/test_blackbox_asset_forge_generation.py`)**:
   - Battlemap generation, tile resolution, obstacle geometry calculation, and Silo S3 bucket verification.
   - Token portrait synthesis, transparent background cropping, and dimensions assertions.
   - Target length: < 220 lines.
2. **Auth, Events & API Contracts Suite (`tests/test_blackbox_asset_forge_auth_and_events.py`)**:
   - CloudEvents registration (`BattlemapForged`, `TokenAssetForged`).
   - Redis Streams event publication and aggregate event sourcing verification.
   - SpiceDB Zanzibar authorization checks (DM role enforcement, 403 Forbidden).
   - Metadata retrieval, 404 behavior, and input validation rejections.
   - Target length: < 220 lines.
3. **Original Monolith Deletion**:
   - Remove `tests/test_blackbox_asset_forge.py`.

## INVEST Criteria Evaluation
- **Independent (I)**: Refactors test structure without altering `services/asset_forge` code or public HTTP endpoints.
- **Negotiable (N)**: Split of assertions across generation and auth suites can be adjusted.
- **Valuable (V)**: Protects against Hard Invariant 6 violations (< 500 lines) and allows isolated generation vs auth verification.
- **Estimable (E)**: Pure test suite decomposition with shared fixtures.
- **Small (S)**: Scope strictly isolated to `tests/test_blackbox_asset_forge.py`; all resulting files < 250 lines.
- **Testable (T)**: Verified with `uv run pytest tests/test_blackbox_asset_forge_*.py`.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Modular Test Suite Partitioning**:
   - `tests/test_blackbox_asset_forge.py` decomposed into `tests/test_blackbox_asset_forge_generation.py` and `tests/test_blackbox_asset_forge_auth_and_events.py`.
2. **Strict File Length Compliance (Hard Invariant 6)**:
   - All resulting test files strictly under 250 lines each.
3. **Frontdoor Blackbox Verification**:
   - 100% test pass rate across all existing asset forge assertions via public HTTP endpoints (`POST /api/v1/forge/battlemap`, `POST /api/v1/forge/token`, `GET /api/v1/forge/assets/{id}`) and Redis Streams.
4. **Original Monolith Removal**:
   - `tests/test_blackbox_asset_forge.py` deleted.
5. **Quality Gates**:
   - Passes `uv run ruff check` and `uv run ruff format --check`.
