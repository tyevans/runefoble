---
id: 0278
title: Settlement Auth and Permissions Modular Decomposition
status: Complete
created: 2026-09-28
dependencies:
- TASK-0259
governing_adrs:
- ADR-0001
- ADR-0003
- ADR-0005
- ADR-0007
- ADR-0013
governing_prds:
- PRD-0024
governing_stories:
- US-0072
- US-0073
target_release: 0.8.0
pr_url: https://github.com/tyevans/runefoble/pull/333
---
# TASK-0278: Settlement Auth and Permissions Modular Decomposition

## Status
Refined

## Summary
Decompose `services/game_session/src/game_session/settlement/auth.py` (385 lines, 77.0% of limit) into modular auth and permission submodules under `services/game_session/src/game_session/settlement/auth/` (`tokens.py`, `permissions.py`, `dependencies.py`), ensuring all auth modules remain strictly < 130 lines per Hard Invariant 6.

## Problem Statement
`services/game_session/src/game_session/settlement/auth.py` bundles Zitadel JWT token extraction, fallback mock auth handlers for local testing, SpiceDB Zanzibar object authorization checks (haven ownership, DM delegation, establishment tenancy), and FastAPI dependency fixtures in a single 385-line file. As multi-party West Marches haven permissions and worker tenancy checks expand, this file will breach the 500-line invariant unless decomposed into cohesive, single-responsibility submodules.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/how-to/define-spicedb-zanzibar-permissions.md`: Schema relations in `runefoble.zed`, writing tuples, and checking permissions.
  - `docs/how-to/authenticate-with-zitadel-oidc.md`: Validating Zitadel JWTs against JWKS discovery and HTTP dependencies.
  - `docs/how-to/charter-frontier-settlements-and-havens.md`: Settlement haven authorization and tenancy boundaries.
- **Governing Architecture & ADRs**:
  - **ADR-0001: SpiceDB Zanzibar Object Authorization**: Fine-grained settlement and haven permission checks.
  - **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean module layout within the `game_session` service.
  - **ADR-0005: Zitadel OIDC Authentication**: Bearer token extraction and user identity parsing.
  - **ADR-0007: Domain-Driven Design Architecture**: Clean domain segregation.
  - **ADR-0013: Modular Decomposition**: All source files kept strictly < 500 lines (submodules < 130 lines).

## Product & User Story References
- Technical debt refactoring supporting:
  - [`prd-0024-settlement-haven-builder-and-mobile-minigames.md`](../../product/accepted/prd-0024-settlement-haven-builder-and-mobile-minigames.md)
  - [`us-0072-mobile-responsive-settlement-browser-and-town-builder.md`](../../user_stories/accepted/us-0072-mobile-responsive-settlement-browser-and-town-builder.md)
  - [`us-0073-customizable-establishments-and-assignable-npc-workers.md`](../../user_stories/accepted/us-0073-customizable-establishments-and-assignable-npc-workers.md)

## Detailed Specification & Implementation Plan
1. **Token Extraction & User Context Submodule (`services/game_session/src/game_session/settlement/auth/tokens.py`)**:
   - Extract Zitadel header parsing, bearer token decoding, and local test mock user context (< 110 lines).
2. **Zanzibar Permission Checks Submodule (`services/game_session/src/game_session/settlement/auth/permissions.py`)**:
   - Extract SpiceDB client helpers for checking haven viewer, builder, DM, and tenant permissions (< 120 lines).
3. **FastAPI Route Dependencies Submodule (`services/game_session/src/game_session/settlement/auth/dependencies.py`)**:
   - Extract FastAPI route dependency injectors (`get_current_settlement_user`, `require_haven_builder`, `require_establishment_manager`) (< 110 lines).
4. **Package Facade (`services/game_session/src/game_session/settlement/auth.py` / `__init__.py`)**:
   - Maintain re-export facade with 100% backwards compatibility for existing imports (< 35 lines).
5. **Verification**:
   - Run settlement test suites to verify auth and permission check parity.

## INVEST Criteria Evaluation
- **Independent (I)**: Refactoring internal auth structure without altering public HTTP endpoints or SpiceDB schema.
- **Negotiable (N)**: Submodule division can be adjusted while keeping files < 130 lines.
- **Valuable (V)**: Protects the largest source file (385 lines) from breaching the 500-line invariant limit.
- **Estimable (E)**: Pure extraction of functions and FastAPI dependencies into focused modules.
- **Small (S)**: Each extracted submodule strictly < 130 lines.
- **Testable (T)**: Existing test suites `test_blackbox_settlements_integration.py` and unit tests verify complete parity.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. `services/game_session/src/game_session/settlement/auth.py` reduced to strictly < 40 lines (or package facade).
2. Extracted submodules under `services/game_session/src/game_session/settlement/auth/` strictly < 130 lines each per Hard Invariant 6.
3. 100% backwards compatibility preserved for all external imports from `game_session.settlement.auth`.
4. Passes all settlement blackbox tests via `uv run pytest tests/test_blackbox_settlements_integration.py tests/test_blackbox_merchant_haggling.py`.
5. Code passes `uv run ruff check .` and `uv run ruff format --check .`.
