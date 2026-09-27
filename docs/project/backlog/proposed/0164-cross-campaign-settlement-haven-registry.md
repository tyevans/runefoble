---
id: '0164'
title: Cross-Campaign Settlement and Haven Registry
status: Proposed
created: 2026-09-26
dependencies:
- TASK-0127
- TASK-0129
governing_adrs:
- ADR-0001
- ADR-0003
- ADR-0006
governing_prds:
- PRD-0018
governing_stories:
- US-0058
target_release: 0.7.0
---

# TASK-0164: Cross-Campaign Settlement and Haven Registry

## Status
Proposed

## Summary
Implement persistent multi-campaign settlement and outpost storage in `services/game_session/`, exposing REST endpoints for charting communal havens, workshops, and resting sanctums across West Marches campaigns.

## Problem Statement
Outposts founded or liberated by one adventuring party currently remain invisible to other parties exploring the same frontier wilderness, preventing shared settlement infrastructure.

## Governing Architecture & ADRs
- **ADR-0001: Zanzibar Fine-Grained Authorization with SpiceDB**: Cross-campaign access scopes.
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean module boundaries.
- **ADR-0006: Redis Streams Distributed Domain Event Streaming**: Shared state notifications.

## Scope of Work
1. **Settlement Registry Aggregate & Storage**:
   - Pydantic models for outposts, fortresses, defensive fortifications, and workshop tiers.
2. **Settlement Management REST Endpoints**:
   - Routes for discovery registration, upgrade contribution, and rest boon queries.
3. **Frontdoor Verification**:
   - Blackbox tests verifying cross-campaign visibility and isolation rules under SpiceDB.

## Definition of Done
- Registry implemented in `services/game_session/src/game_session/`.
- FastMCP tool exposed for outpost inspections.
- Tests pass via `uv run pytest`.
- File length remains under 250 lines.
