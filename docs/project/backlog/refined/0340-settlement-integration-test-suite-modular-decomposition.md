---
id: '0340'
title: Settlement Integration Test Suite Modular Decomposition
status: Refined
created: 2026-09-28
dependencies:
- TASK-0264
- TASK-0278
- TASK-0280
governing_adrs:
- ADR-0001
- ADR-0003
- ADR-0006
- ADR-0007
- ADR-0009
- ADR-0010
- ADR-0013
governing_prds:
- PRD-0024
governing_stories:
- US-0072
- US-0073
- US-0075
- US-0076
target_release: 0.8.0
---

# TASK-0340: Settlement Integration Test Suite Modular Decomposition

## Status
Refined

## Summary
Decompose `tests/test_blackbox_settlements_integration.py` (497 lines, 99.4% of the 500-line invariant limit) into modular test submodules under `tests/test_blackbox_settlements_integration/` (`conftest.py`, `test_invariants_and_compat.py`, `test_auth_and_permissions.py`, `test_settlement_and_establishments.py`, `test_haggling_and_bulletin.py`), ensuring all test modules remain strictly < 130 lines per Hard Invariant 6.

## Problem Statement
Following the modular decomposition of settlement authentication and worker routers (TASK-0278, TASK-0280), `tests/test_blackbox_settlements_integration.py` reached 497 lines. It bundles line invariant verifications, backwards-compatibility checks, bearer token auth lifecycles, settlement founding, tier upgrades, establishment creation, assignable NPC workers, merchant haggling gambits, and bulletin board notice decryption in a single monolithic test file. Operating within 3 lines of breaching Hard Invariant 6 (<500 lines), it is an urgent refactoring candidate that must be decomposed immediately to prevent invariant violations.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/how-to/build-settlements-and-play-mobile-minigames.md`: Settlement creation, tier upgrades, and establishment lifecycles.
  - `docs/how-to/run-tavern-minigames-and-merchant-haggling.md`: Merchant bargaining gambits and DM intervention.
  - `docs/reference/tavern-and-merchants-events.md`: Settlement and merchant CloudEvents schemas.
- **Governing Architecture & ADRs**:
  - **ADR-0001: Fine-Grained Authorization with SpiceDB Zanzibar Schema**: Zanzibar object permissions for settlement ownership and mayor roles.
  - **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean module layout and isolated test execution.
  - **ADR-0006: Redis Streams Distributed Domain Event Streaming**: Event broadcasting across settlement, tavern, and West Marches streams.
  - **ADR-0007: Domain-Driven Design Architecture**: Clean frontdoor testing across service aggregates.
  - **ADR-0009: Code Quality and Linting with Ruff and Pre-commit**: Code formatting and linting standards.
  - **ADR-0010: Continuous Integration Pipeline**: Rapid and modular test suite execution.
  - **ADR-0013: Microfrontend Architecture and Service Component Vendoring**: Single-responsibility test modules strictly < 130 lines.

## Product & User Story References
- Technical debt refactoring supporting:
  - [`prd-0024-settlement-haven-builder-and-mobile-minigames.md`](../../product/accepted/prd-0024-settlement-haven-builder-and-mobile-minigames.md)
  - [`us-0072-settlement-haven-builder-and-communal-facilities.md`](../../user_stories/accepted/us-0072-settlement-haven-builder-and-communal-facilities.md)
  - [`us-0073-assignable-npc-workers-and-social-relationship-graph.md`](../../user_stories/accepted/us-0073-assignable-npc-workers-and-social-relationship-graph.md)
  - [`us-0075-dynamic-merchant-haggling-with-dm-arbitration.md`](../../user_stories/accepted/us-0075-dynamic-merchant-haggling-with-dm-arbitration.md)
  - [`us-0076-town-bulletin-board-civic-notices-and-bounties.md`](../../user_stories/accepted/us-0076-town-bulletin-board-civic-notices-and-bounties.md)

## Detailed Specification & Implementation Plan
1. **Shared Fixtures & Stream Utilities (`tests/test_blackbox_settlements_integration/conftest.py`)**:
   - Extract `mock_bus`, `spicedb`, `session_client`, `gateway_client`, `clean_gateway_ws`, `assert_stream_event`, and `_assert_submodules` (< 90 lines).
2. **Line Invariant & Compatibility Tests (`tests/test_blackbox_settlements_integration/test_invariants_and_compat.py`)**:
   - Extract `test_modular_submodule_line_invariants`, `test_auth_backwards_compatibility_exports`, and `test_workers_backwards_compatibility_exports` (< 95 lines).
3. **Authentication & Route Dependency Tests (`tests/test_blackbox_settlements_integration/test_auth_and_permissions.py`)**:
   - Extract `test_bearer_token_extraction_and_decoding`, `test_fastapi_route_dependencies`, and `test_frontdoor_settlement_auth_lifecycle` (< 85 lines).
4. **Settlement Lifecycle & Worker Tests (`tests/test_blackbox_settlements_integration/test_settlement_and_establishments.py`)**:
   - Extract `test_found_settlement_and_upgrade_tier_flow` and `test_establishment_creation_and_worker_assignment` (< 110 lines).
5. **Haggling Gambits & Bulletin Board Tests (`tests/test_blackbox_settlements_integration/test_haggling_and_bulletin.py`)**:
   - Extract `test_merchant_haggling_gambits_and_dm_override` and `test_bulletin_board_pin_and_cipher_decrypt` (< 115 lines).
6. **Verification**:
   - Safely remove monolithic `tests/test_blackbox_settlements_integration.py` and ensure `uv run pytest tests/test_blackbox_settlements_integration/` runs with 100% passing tests.

## INVEST Criteria Evaluation
- **Independent (I)**: Pure test suite refactoring without altering any production endpoints or schemas.
- **Negotiable (N)**: Submodule file boundaries and helper distribution can be adapted cleanly.
- **Valuable (V)**: Defuses imminent breach of Hard Invariant 6 (<500 lines) on the largest source file in the repository (497 lines).
- **Estimable (E)**: Clearly mapped test functions and fixtures with known passing assertions.
- **Small (S)**: Each extracted test submodule strictly < 130 lines.
- **Testable (T)**: Directly executable via `uv run pytest tests/test_blackbox_settlements_integration/`.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. `tests/test_blackbox_settlements_integration.py` decomposed into `tests/test_blackbox_settlements_integration/` test package.
2. All extracted submodules strictly < 130 lines per Hard Invariant 6.
3. 100% of test assertions pass via `uv run pytest tests/test_blackbox_settlements_integration/`.
4. Monolithic `tests/test_blackbox_settlements_integration.py` safely removed.
5. Code passes `uv run ruff check .` and `uv run ruff format --check .`.
