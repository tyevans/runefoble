---
id: 0052
title: Campaign Analytics & Chronicle Archive Microservice
status: Proposed
created: 2026-09-25
dependencies: [TASK-0011, TASK-0015, TASK-0032]
governing_adrs: [ADR-0006, ADR-0007]
target_release: 0.3.0
---

# TASK-0052: Campaign Analytics & Chronicle Archive Microservice

## Status
Proposed

## Summary
Scaffold a new bounded context `services/campaign_analytics` to project combat telemetry, damage heatmaps, party MVP metrics, and an interactive historical campaign timeline from Redis Streams events.

## Problem Statement
Returning players (Sarah) and DMs (Evelyn) have no aggregated historical telemetry to understand tactical performance, pacing issues, or long-term character milestones across multi-month campaigns.

## Scope of Work
1. **Service Scaffolding**: Create `services/campaign_analytics` in UV monorepo.
2. **Telemetry Projection Worker**: Consume domain events from Redis Streams (`CombatTurnCompleted`, `CharacterDamaged`, `DiceRolled`) into partitioned analytical tables in PostgreSQL.
3. **Heatmap & Metrics Engine**: Compute spatial coordinate damage heatmaps and per-encounter MVP awards.
4. **Interactive Timeline API**: Expose historical timeline nodes linking chronicles, boss fights, and loot rewards.

## Acceptance Criteria
1. Real-time projection latency under 200ms from Redis Streams event publication.
2. Spatial heatmap endpoint outputs aggregated hit/damage densities per board coordinate.
3. Timeline endpoint returns chronological milestone entries with session recap links.
