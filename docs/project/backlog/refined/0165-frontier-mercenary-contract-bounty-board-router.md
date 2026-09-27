---
id: '0165'
title: Frontier Mercenary Contract and Bounty Board Router
status: Refined
created: 2026-09-26
dependencies:
- TASK-0129
- TASK-0136
governing_adrs:
- ADR-0001
- ADR-0003
- ADR-0005
- ADR-0006
- ADR-0007
governing_prds:
- PRD-0018
governing_stories:
- US-0058
target_release: 0.7.0
---

# TASK-0165: Frontier Mercenary Contract and Bounty Board Router

## Status
Refined

## Summary
Implement modular API endpoints and contract lifecycle handlers in `services/game_session/` for posting, claiming, verifying, and completing mercenary bounties and resource retrieval contracts between different adventuring parties sharing a West Marches frontier.

## Problem Statement
While caravan trading ledgers exist, parties exploring a persistent West Marches frontier lack an asynchronous in-world mechanism to commission fellow adventuring parties for dangerous monster hunting or rare material harvesting, with escrowed payouts and Zanzibar-protected claim verification.

## Governing Architecture & ADRs
- **ADR-0001: Zanzibar Fine-Grained Authorization with SpiceDB**: Multi-campaign party permissions, bounty claiming scopes, and creator authorization.
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean module layout in `services/game_session/src/game_session/contracts/`.
- **ADR-0005: Zitadel Production OIDC/JWKS Token Verification**: Authentication dependency for party leaders.
- **ADR-0006: Redis Streams Distributed Domain Event Streaming**: Contract state fanout to `runefoble:events:session`.
- **ADR-0007: Domain-Driven Design Architecture**: Clean domain segregation for contract lifecycle states and reward escrow.

## Product & User Story References
- **Product Requirement**: [`prd-0018-west-marches-shared-world-state-and-cross-campaign-trade.md`](../../product/accepted/prd-0018-west-marches-shared-world-state-and-cross-campaign-trade.md)
- **User Story**: [`us-0058-west-marches-shared-world-state-and-caravan-trade.md`](../../user_stories/accepted/us-0058-west-marches-shared-world-state-and-caravan-trade.md)

## Detailed Specification & Implementation Plan
1. **Contract Lifecycle Domain Engine (`services/game_session/src/game_session/contracts/engine.py`)**:
   - Manages state transitions: `POSTED`, `ACCEPTED`, `FULFILLED`, `DISPUTED`, and `COMPLETED` with escrow locks (< 140 lines).
2. **SpiceDB Contract Permissions (`services/game_session/src/game_session/contracts/auth.py`)**:
   - Validate creator, claimant, and escrow disbursement permissions using SpiceDB relations (< 110 lines).
3. **CloudEvents Registration (`libs/runefoble_events/src/runefoble_events/contracts.py`)**:
   - Define `MercenaryBountyPostedEvent`, `MercenaryBountyClaimedEvent`, and `MercenaryBountyFulfilledEvent` (< 80 lines).
4. **Bounty Board APIRouter (`services/game_session/src/game_session/routers/bounties.py`)**:
   - `POST /sessions/{session_id}/contracts/bounties`: Post new bounty with gold/item escrow.
   - `GET /sessions/{session_id}/contracts/bounties`: Query open board bounties.
   - `POST /sessions/{session_id}/contracts/bounties/{bounty_id}/claim`: Claim active bounty.
   - `POST /sessions/{session_id}/contracts/bounties/{bounty_id}/complete`: Submit proof and disburse escrow (< 150 lines).

## INVEST Criteria Evaluation
- **Independent (I)**: Functions cleanly across campaigns without modifying active round-by-round combat turns.
- **Negotiable (N)**: Escrow fee percentages and expiration windows are configurable.
- **Valuable (V)**: Fosters asynchronous cooperation and player-driven economies in shared West Marches worlds.
- **Estimable (E)**: Standard REST router backed by SpiceDB authorization checks and CloudEvents.
- **Small (S)**: Bounded strictly to `services/game_session/src/game_session/contracts/`; all modules < 160 lines.
- **Testable (T)**: Frontdoor blackbox tests verify contract posting, claim transitions, authorization locks, and escrow release.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Domain Engine & Handlers**:
   - `services/game_session/src/game_session/contracts/` created with focused submodules.
   - All modules strictly < 160 lines per Hard Invariant 6.
2. **Frontdoor Test Verification**:
   - Blackbox test suite `tests/test_blackbox_bounty_contracts/` verifies full lifecycle through REST frontdoor.
3. **Quality Gates**:
   - Passes `uv run pytest tests/test_blackbox_bounty_contracts/`, `uv run ruff check .`, and `uv run ruff format --check .`.
