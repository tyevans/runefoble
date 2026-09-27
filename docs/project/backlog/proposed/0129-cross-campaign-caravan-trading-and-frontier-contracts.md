---
id: '0129'
title: Cross-Campaign Caravan Trading Ledgers & Frontier Mercenary Contracts
status: Proposed
created: 2026-09-26
dependencies:
- TASK-0127
governing_adrs:
- ADR-0001
- ADR-0006
- ADR-0011
target_release: 0.5.0
prd_url: docs/project/product/accepted/prd-0007-campaign-worldbuilding-lore-and-rag-engine.md
user_story: US-0058
---

# TASK-0129: Cross-Campaign Caravan Trading Ledgers & Frontier Mercenary Contracts

## Status
Proposed

## Summary
Expand West Marches community play by introducing asynchronous mercenary contracts and caravan trading ledgers, allowing adventuring parties to post bounties and supply caravans that other parties can escort or ambush during their sessions.

## Problem Statement
While shared frontier discovery is enabled by TASK-0127, parties still lack structured economic and narrative interdependence. Guild masters need an asynchronous bounty and caravan escort system to coordinate multi-party campaign arcs.

## Governing Architecture & ADRs
- **ADR-0001**: SpiceDB Zanzibar access control on trade contracts.
- **ADR-0006**: Redis Streams event streaming for caravan transit status.
- **ADR-0011**: eventsource-py aggregate persistence for caravan trade manifests.

## Scope of Work
1. **Caravan Manifest & Contract Domain**:
   - `CaravanContractAggregate` modeling cargo value, route risk, escort payout, and destination settlement.
2. **Asynchronous Multi-Party Bounties**:
   - Outpost boards displaying active guild contracts accepted by separate adventuring groups.
3. **Dynamic Settlement Economy Effects**:
   - Successful caravan arrivals reducing local merchant prices and unlocking rare materials.
4. **Frontdoor Blackbox Verification**:
   - Blackbox test suite verifying contract creation, claim verification, and reward distribution.
