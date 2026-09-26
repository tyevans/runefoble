---
id: 0049
title: Procedural Battlemap & Token Asset Forge Microservice
status: Complete
created: 2026-09-25
dependencies:
- TASK-0004
- TASK-0007
- TASK-0023
- TASK-0047
- TASK-0048
governing_adrs:
- ADR-0003
- ADR-0005
- ADR-0006
- ADR-0010
- ADR-0011
- ADR-0013
target_release: 0.3.0
pr_url: https://github.com/tyevans/runefoble/pull/61
---
# TASK-0049: Procedural Battlemap & Token Asset Forge Microservice

## Status
Refined

## Summary
Scaffold a new bounded context microservice `services/asset_forge` integrating procedural diffusion prompts, obstacle/wall segmentation, and token portrait generation saved directly to Silo S3 with automated geometry projection into `board_state`.

## Problem Statement
Finding, aligning, sizing, and drawing line-of-sight walls on battlemaps consumes hours of human DM preparation time (PRD-0009). Tabletop DMs need natural spoken or prompted generation (*"Subterranean dwarven forge with lava canals and broken anvil statues"*) that yields game-ready tactical maps with pre-calculated wall collisions and hazard grids in under 15 seconds.

## Governing Architecture & ADRs
- **ADR-0003**: UV Monorepo Workspace for Python Bounded Contexts (`services/asset_forge`).
- **ADR-0005**: Kubernetes-First Infrastructure with Helm and Kind (`deployments/helm/runefoble/templates/asset-forge.yaml`).
- **ADR-0006**: Redis Streams Event Bus Transport (publishing `AssetGenerated` and `BattlemapCreated` events).
- **ADR-0010**: OpenTelemetry Distributed Tracing & Metrics instrumentation.
- **ADR-0011**: eventsource-py Core Event Sourcing (`AssetForgeAggregate` and repositories).
- **ADR-0013**: Microfrontend Architecture and Service Component Vendoring (`/ui/manifest` and Storybook).

## Scope of Work
1. **UV Monorepo Package Scaffolding (`services/asset_forge`)**:
   - Initialize bounded context package registered in root `pyproject.toml`.
   - Setup FastAPI application exposing `/healthz`, `/openapi.json`, and `/ui/manifest`.
2. **Procedural Generation Pipeline**:
   - Synthesizer generating structured battlemap grid tiles and obstacle geometry from prompts.
   - Circular token portrait cropping and transparent background synthesis.
3. **Silo S3 Media Storage Integration**:
   - Automated upload of generated raster maps and token PNGs to MinIO/Silo S3 media buckets with presigned URLs.
4. **Spatial Geometry Projection**:
   - Extraction of wall segments, doors, and hazardous terrain cells (lava, water) formatted for `board_state` mutators.
5. **Frontdoor Blackbox Verification**:
   - Comprehensive test suite in `tests/test_blackbox_asset_forge.py`.

## INVEST Criteria Evaluation
- **Independent (I)**: Operates as an autonomous microservice communicating via standard HTTP REST endpoints and CloudEvents.
- **Negotiable (N)**: Image generation backend (mock generator, Stable Diffusion, or external API) can be swapped via configuration.
- **Valuable (V)**: Drastically reduces DM game preparation friction (core platform value proposition in PRD-0009).
- **Estimable (E)**: Follows the established microservice pattern instantiated by `campaign_lore` (TASK-0047) and `rules_compendium` (TASK-0048).
- **Small (S)**: Bounded context modularly divided across routers, generator, storage, and models; all files < 300 lines.
- **Testable (T)**: Fully verifiable via public HTTP API routes (`POST /api/v1/forge/battlemap`, `POST /api/v1/forge/token`) and Silo asset URL queries.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Bounded Context Scaffolding**:
   - `services/asset_forge` added to root `pyproject.toml` workspace and passing `uv run pytest`.
2. **Public HTTP Frontdoor API**:
   - `POST /api/v1/forge/battlemap`: Generates map texture, calculates wall segments, uploads to Silo S3, returns presigned URL and geometry.
   - `POST /api/v1/forge/token`: Generates transparent circular token portrait and stores in Silo S3.
   - `GET /healthz` and `GET /ui/manifest` exposed.
3. **Domain Event Publication**:
   - Emits CloudEvents `BattlemapForged` and `TokenAssetForged` over Redis Streams.
4. **Helm Integration**:
   - Deployment, Service, and ConfigMap added to umbrella Helm chart.
5. **Frontdoor Blackbox Test Suite**:
   - `tests/test_blackbox_asset_forge.py` verifying full generation, storage, and geometry extraction through public routes.
6. **Quality Gates**:
   - Passes `uv run ruff check` and `uv run ruff format --check`.
