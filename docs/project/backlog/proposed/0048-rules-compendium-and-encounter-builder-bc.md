---
id: 0048
title: TTRPG Rules Compendium & Automated Encounter Builder Microservice
status: Proposed
created: 2026-09-25
dependencies: [TASK-0001, TASK-0009, TASK-0018]
governing_adrs: [ADR-0007, ADR-0011]
target_release: 0.3.0
---

# TASK-0048: TTRPG Rules Compendium & Automated Encounter Builder Microservice

## Status
Proposed

## Summary
Scaffold a new bounded context microservice `services/rules_compendium` providing structured SRD 5.1/ORC rules lookups (monsters, spells, feats, conditions) and an automated Challenge Rating (CR) encounter balancing engine.

## Problem Statement
Combat encounter preparation is a primary time sink for DMs (Evelyn). Currently, monster stats and rules are either simulated or hardcoded, leading to inconsistent rules adjudication during live sessions.

## Scope of Work
1. **Service Scaffolding**: Create `services/rules_compendium` in UV monorepo.
2. **SRD / ORC Rules Index**: Ingest and index canonical monster stat blocks, spell definitions, and condition rules.
3. **CR Balancing Algorithm**: Implement encounter budget calculation (Party Size $\times$ Level vs. Enemy XP Thresholds).
4. **FastMCP Integration**: Expose compendium lookup tools (`query_monster_stat_block`, `calculate_encounter_balance`) to gateway MCP.

## Acceptance Criteria
1. Sub-50ms query latency for monsters and spells.
2. Accurate CR lethality scoring for arbitrary party sizes and levels.
3. Support for user-defined homebrew spells and creatures.
