---
id: '0052'
title: Campaign Analytics & Chronicle Archive Microservice
status: Complete
created: 2026-09-25
dependencies:
- TASK-0011
- TASK-0015
- TASK-0036
- TASK-0038
governing_adrs:
- ADR-0003
- ADR-0005
- ADR-0006
- ADR-0011
target_release: 0.3.0
governing_prds:
- PRD-0012
governing_stories:
- US-0040
- US-0054
pr_url: https://github.com/tyevans/runefoble/pull/97
---
# TASK-0052: Campaign Analytics & Chronicle Archive Microservice

## Status
Refined

## Summary
Scaffold the `services/campaign_analytics` bounded context microservice to project combat telemetry, tactical damage heatmaps, party MVP turn statistics, and interactive campaign milestone timelines from distributed Redis Streams domain events into PostgreSQL.

## Problem Statement
Returning players (Sarah) and human DMs (Evelyn) currently lack aggregated historical telemetry to assess combat pacing, character milestones, hazard lethality, and party tactics across extended campaign arcs (PRD-0012, US-0040, US-0054).

## Governing Architecture & ADRs
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Scaffolding `services/campaign_analytics` within root workspace pyproject.toml.
- **ADR-0005: Kubernetes-First Infrastructure with Helm and Kind**: Registering service deployment, service port 8009, and ingress routes.
- **ADR-0006: Redis Streams Distributed Event Bus**: Real-time event consumption via dedicated consumer group `campaign_analytics_worker`.
- **ADR-0011: eventsource-py Core Event Sourcing**: Read-model projections written to persistent PostgreSQL tables.

## Product & User Story References
- **Product Requirement**: [`prd-0012-campaign-telemetry-and-living-chronicle-timeline.md`](../../product/accepted/prd-0012-campaign-telemetry-and-living-chronicle-timeline.md)
- **User Stories**:
  - [`us-0040-campaign-combat-telemetry-and-living-timeline.md`](../../user_stories/accepted/us-0040-campaign-combat-telemetry-and-living-timeline.md)
  - [`us-0054-combat-spatial-heatmaps-and-party-damage-analytics.md`](../../user_stories/accepted/us-0054-combat-spatial-heatmaps-and-party-damage-analytics.md)

## Detailed Specification & Implementation Plan
1. **Service Scaffolding & FastAPI App**:
   - Create `services/campaign_analytics` with FastAPI application exposing `/healthz`, `/metrics`, and `/openapi.json`.
   - Wire dependencies into root `pyproject.toml` and Helm values.
2. **Telemetry Projection Worker**:
   - Implement `CampaignAnalyticsWorker` consuming Redis Streams events (`CombatRoundAdvanced`, `CharacterHealthChanged`, `DiceRolled`, `TokenMoved`, `SessionEnded`).
   - Project spatial coordinates, damage values, and status condition timestamps into PostgreSQL analytical tables.
3. **Analytics REST Endpoints**:
   - `GET /api/v1/analytics/campaigns/{id}/heatmap`: Aggregated spatial coordinate hit/damage densities.
   - `GET /api/v1/analytics/campaigns/{id}/mvp`: Per-encounter MVP awards based on damage dealt, healing provided, and critical hits.
   - `GET /api/v1/analytics/campaigns/{id}/timeline`: Chronological event milestones linking session recaps and boss encounters.
4. **Frontdoor Blackbox Verification**:
   - Create `tests/test_blackbox_campaign_analytics.py` verifying event consumption, projection latency (< 200ms), and REST query responses.

## INVEST Criteria Evaluation
- **Independent (I)**: Consumes standard CloudEvents from Redis Streams without modifying publishing microservices.
- **Negotiable (N)**: Heatmap coordinate bucketing granularity (e.g. 5ft vs 10ft cells) can be configured.
- **Valuable (V)**: Provides essential campaign retrospective insights for players and DMs.
- **Estimable (E)**: Follows established pattern of Redis consumer projection workers and FastAPI APIRouters.
- **Small (S)**: Scope isolated to new bounded context; all files strictly < 300 lines.
- **Testable (T)**: Tested strictly through public frontdoor REST endpoints and Redis stream publishing.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Public REST APIs**:
   - `GET /api/v1/analytics/campaigns/{id}/heatmap` returns coordinate-based density matrices.
   - `GET /api/v1/analytics/campaigns/{id}/timeline` returns chronological session milestones.
2. **Infrastructure & OpenAPI**:
   - `/openapi.json` exposed and registered in Helm `values.yaml`.
   - Health check `/healthz` returning 200 OK.
3. **Frontdoor Blackbox Test Suite**:
   - `tests/test_blackbox_campaign_analytics.py` publishes domain CloudEvents to Redis Streams and asserts projected REST responses.
4. **Quality Gates**:
   - Conforms strictly to Hard Invariant 6 (< 500 lines per file).
   - Passes `uv run pytest tests/test_blackbox_campaign_analytics.py` and `uv run ruff check`.
