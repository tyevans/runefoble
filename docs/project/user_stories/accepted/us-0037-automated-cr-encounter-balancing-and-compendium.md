---
id: 0037
title: Automated CR Encounter Balancing & redstring Rules Indexing
status: Shipped
created: 2026-09-25
governing_prd: PRD-0008
---

# US-0037 — Automated CR Encounter Balancing & redstring Rules Indexing

## Governing PRD
- [`PRD-0008: TTRPG Rules Compendium & Automated Encounter Builder`](../../product/accepted/prd-0008-ttrpg-rules-compendium-and-encounter-builder.md)

## User Story

**As an** overworked Dungeon Master prepping weekly combat sessions (Evelyn),  
**I want to** generate mathematically balanced encounters and query canonical rules indexed with `redstring`,  
**So that** combat challenges are fair and exciting while prep time drops from hours to seconds.

## Acceptance Criteria

1. **CR Budget Calculation**: Calculates accurate encounter difficulty thresholds (Easy, Medium, Hard, Deadly) for any party size and level.
2. **redstring BM25 & Semantic Search**: Spells, monster stat blocks, and condition rules are indexed through `redstring` for sub-50ms BM25 and vector queries.
3. **Synergistic Monster Generation**: Proposes enemy combinations with diverse combat roles (brute, artillery, controller).
