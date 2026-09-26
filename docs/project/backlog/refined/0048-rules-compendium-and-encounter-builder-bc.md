---
id: '0048'
title: TTRPG Rules Compendium & Automated Encounter Builder Microservice
status: Refined
created: 2026-09-25
dependencies:
- TASK-0001
- TASK-0008
- TASK-0009
- TASK-0018
governing_adrs:
- ADR-0001
- ADR-0003
- ADR-0006
- ADR-0007
- ADR-0009
- ADR-0011
target_release: 0.3.0
---

# TASK-0048: TTRPG Rules Compendium & Automated Encounter Builder Microservice

## Status
Refined

## Summary
Scaffold a new bounded context microservice `services/rules_compendium` in the UV monorepo workspace powered by `redstring` (`tyevans/redstring` on GitHub / PyPI). The service ingests canonical SRD 5.1 and ORC rules (monsters, spells, conditions, feats, action economy rules), provides sub-50ms hybrid BM25 and vector retrieval, implements an automated Challenge Rating (CR) encounter balancing engine, and exposes lookup tools to FastMCP.

## Problem Statement
DMs (Evelyn) spend hours manually looking up monster stats, verifying spell descriptions, and computing Challenge Rating (CR) XP thresholds for combat encounters. During live gameplay, adjudicating rules disputes or improvising enemy reinforcement groups stalls combat for minutes, degrading session momentum. A structured, low-latency compendium and mathematically grounded encounter builder eliminates manual prep time and enables instant in-session arbitration by The Watcher.

## PRD & User Story Alignment
- **Governing PRD**: [`prd-0008-ttrpg-rules-compendium-and-encounter-builder.md`](../../product/accepted/prd-0008-ttrpg-rules-compendium-and-encounter-builder.md)
- **User Story**: [`us-0037-automated-cr-encounter-balancing-and-compendium.md`](../../user_stories/accepted/us-0037-automated-cr-encounter-balancing-and-compendium.md)

## Governing Architecture & ADRs
- **ADR-0001**: SpiceDB Zanzibar Object-Level Authorization (public SRD rules accessible to all; user homebrew entries restricted by campaign ownership).
- **ADR-0003**: UV Monorepo Workspace for Python Bounded Contexts (`services/rules_compendium`).
- **ADR-0006**: Redis Streams Event Bus Infrastructure (publish `EncounterBalanced`, `HomebrewRuleRegistered` events).
- **ADR-0007**: API Gateway Architecture and FastMCP Tool Integration (`query_monster_stat_block`, `calculate_encounter_balance`).
- **ADR-0009**: Code Quality and Linting with Ruff (strict file length invariant < 500 lines).
- **ADR-0011**: eventsource-py Core Event Sourcing Architecture (`CompendiumAggregate`, `EncounterAggregate`).

## Proposed Architecture & Technical Plan
1. **UV Monorepo Integration (`services/rules_compendium`)**:
   - Initialize `services/rules_compendium` package and register it under workspace members in `pyproject.toml`.
   - Add `redstring[redis,llm]` and `eventsource-py` dependencies.
2. **Rules Compendium Aggregate & Ingestion (`services/rules_compendium/src/rules_compendium/`)**:
   - `aggregate.py`: Declarative aggregates for `CompendiumAggregate` and `EncounterAggregate` inheriting from `eventsource-py`.
   - Domain events: `MonsterIndexed`, `SpellIndexed`, `ConditionIndexed`, `HomebrewRuleRegistered`, `EncounterBalanced`.
   - Ingestion loader for canonical SRD 5.1 JSON/markdown datasets into `redstring` hybrid knowledge index.
3. **CR Balancing Engine (`services/rules_compendium/src/rules_compendium/encounter_builder.py`)**:
   - Mathematical model calculating party adjusted XP thresholds (Easy, Medium, Hard, Deadly) across arbitrary party size and level vectors.
   - Action economy multiplier calculation based on enemy count vs party size.
   - Synergistic creature selection algorithm balancing frontline brutes, ranged artillery, and controllers.
4. **Public HTTP Frontdoor API (`services/rules_compendium/src/rules_compendium/main.py` & routers)**:
   - `GET /api/v1/compendium/rules/search`: Hybrid BM25 and semantic lookup for spells, monsters, and conditions.
   - `POST /api/v1/compendium/encounters/balance`: Compute encounter lethality and recommend monster group configurations for a given party roster.
   - `POST /api/v1/compendium/homebrew`: Register custom campaign homebrew monsters or rules guarded by SpiceDB Zanzibar permissions.
   - `/openapi.json`: OpenAPI spec exposition for Swagger UI aggregator.
5. **FastMCP Tabletop Tools**:
   - Register `query_monster_stat_block` and `calculate_encounter_balance` MCP tools on gateway.

## INVEST Criteria Evaluation
- **Independent (I)**: Completely self-contained bounded context microservice interacting strictly via standard HTTP REST, Redis Streams, and FastMCP tools.
- **Negotiable (N)**: Encounter generator weighting (role distribution vs lethality tier) can be tuned without changing public endpoint contracts.
- **Valuable (V)**: Reduces DM combat preparation from hours to seconds and provides instant rule lookup for players and The Watcher.
- **Estimable (E)**: Built on standard `eventsource-py`, `redstring`, and FastAPI patterns established in earlier microservices.
- **Small (S)**: Scope strictly isolated to `services/rules_compendium` scaffolding, encounter algorithm, and frontdoor test suite; each source file strictly < 300 lines.
- **Testable (T)**: Tested strictly through public HTTP frontdoors (`POST /api/v1/compendium/encounters/balance`, `GET /api/v1/compendium/rules/search`) with blackbox assertions.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Bounded Context Scaffolding**:
   - `services/rules_compendium` created and verified in UV monorepo workspace.
2. **Frontdoor Blackbox Test Suite**:
   - Blackbox test suite created at `tests/test_blackbox_rules_compendium.py` verifying:
     - Canonical rule lookup via `GET /api/v1/compendium/rules/search` (sub-50ms latency budget).
     - Accurate CR XP threshold calculation for arbitrary party size and levels via `POST /api/v1/compendium/encounters/balance`.
     - Homebrew rule registration and SpiceDB ownership isolation via `POST /api/v1/compendium/homebrew`.
     - FastMCP tools registered and invokable.
3. **Hard Invariant Compliance**:
   - Zero files exceeding 500 lines (Hard Invariant 6).
   - Domain events inherit from `BaseRunefobleEvent` and state transitions use `eventsource-py` (Hard Invariant 2).
   - OpenAPI specifications exposed at `/openapi.json` (Hard Invariant 5).
4. **Automated Quality Gates**:
   - `uv run pytest tests/test_blackbox_rules_compendium.py` passes 100%.
   - `uv run ruff check services/rules_compendium` and `uv run ruff format --check services/rules_compendium` pass cleanly.
