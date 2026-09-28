---
id: '0278'
title: Settlement Auth and Permissions Modular Decomposition
status: Proposed
created: 2026-09-28
dependencies:
- TASK-0259
governing_adrs:
- ADR-0001
- ADR-0003
- ADR-0005
- ADR-0007
governing_prds:
- PRD-0024
governing_stories:
- US-0072
- US-0073
target_release: 0.8.0
---

# TASK-0278: Settlement Auth and Permissions Modular Decomposition

## Status
Proposed

## Summary
Decompose `services/game_session/src/game_session/settlement/auth.py` (364 lines, 72.8% of limit) into modular auth and permission submodules under `services/game_session/src/game_session/settlement/auth/` (`tokens.py`, `permissions.py`, `dependencies.py`), ensuring all auth modules remain strictly < 130 lines per Hard Invariant 6.

## Problem Statement
`services/game_session/src/game_session/settlement/auth.py` bundles Zitadel JWT token extraction, fallback mock auth handlers for local testing, SpiceDB Zanzibar object authorization checks (haven ownership, DM delegation, establishment tenancy), and FastAPI dependency fixtures in a single 364-line file. As multi-party West Marches haven permissions and worker tenancy checks expand, this file will breach the 500-line invariant unless decomposed.

## Governing Architecture & ADRs
- **ADR-0001: SpiceDB Zanzibar Object Authorization**: Fine-grained settlement and haven permission checks.
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean module structuring within bounded contexts.
- **ADR-0005: Zitadel OIDC Authentication**: Bearer token extraction and user identity parsing.
- **ADR-0007: Domain-Driven Design Architecture**: Clean domain segregation.

## Scope of Work
1. **Token Extraction & User Context (`services/game_session/src/game_session/settlement/auth/tokens.py`)**:
   - Extract Zitadel header parsing, bearer token decoding, and local test mock user context (< 110 lines).
2. **Zanzibar Permission Checks (`services/game_session/src/game_session/settlement/auth/permissions.py`)**:
   - Extract SpiceDB client helpers for checking haven viewer, builder, DM, and tenant permissions (< 120 lines).
3. **FastAPI Dependencies (`services/game_session/src/game_session/settlement/auth/dependencies.py`)**:
   - Extract FastAPI route dependency injectors (`get_current_settlement_user`, `require_haven_builder`, `require_establishment_manager`) (< 110 lines).
4. **Aggregator Facade (`services/game_session/src/game_session/settlement/auth.py`)**:
   - Maintain re-export facade with full backwards compatibility (< 35 lines).
5. **Verification**:
   - Run settlement test suites to verify auth and permission check parity.

## Definition of Done
- `services/game_session/src/game_session/settlement/auth.py` reduced to strictly < 40 lines.
- Extracted submodules under `auth/` strictly < 130 lines each.
- Passes all settlement blackbox test suites.
- Code passes `uv run ruff check .` and `uv run ruff format --check .`.
