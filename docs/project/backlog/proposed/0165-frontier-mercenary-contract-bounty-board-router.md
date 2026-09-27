---
id: '0165'
title: Frontier Mercenary Contract and Bounty Board Router
status: Proposed
created: 2026-09-26
dependencies:
- TASK-0129
- TASK-0136
governing_adrs:
- ADR-0001
- ADR-0003
- ADR-0005
governing_prds:
- PRD-0018
governing_stories:
- US-0058
target_release: 0.7.0
---

# TASK-0165: Frontier Mercenary Contract and Bounty Board Router

## Status
Proposed

## Summary
Implement modular API endpoints in `services/game_session/` for posting, claiming, and validating mercenary bounties and resource retrieval contracts between different parties sharing a West Marches world.

## Problem Statement
Parties need an asynchronous, in-world mechanism to commission fellow adventurers for monster hunting or rare reagent gathering, with escrowed reward payouts that prevent fraud or duplicate claims.

## Governing Architecture & ADRs
- **ADR-0001: Zanzibar Fine-Grained Authorization with SpiceDB**: Contract edit permissions.
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Dedicated router module.
- **ADR-0005: Zitadel Production OIDC/JWKS Token Verification**: Authentication dependency.

## Scope of Work
1. **Contract Posting & Escrow Routes**:
   - Endpoints for creating contracts with deposit escrow and expiration timestamps.
2. **Claiming & Completion Handshake**:
   - Validation workflow ensuring party eligibility and payout distribution upon proof submission.
3. **Frontdoor Verification**:
   - Blackbox tests validating contract lifecycles, expiration sweeps, and Zanzibar authorization.

## Definition of Done
- Router added to `services/game_session/src/game_session/routers/`.
- OpenAPI schema documented and aggregated in Swagger UI.
- Test suite passes cleanly with `uv run pytest`.
- Router length under 250 lines.
