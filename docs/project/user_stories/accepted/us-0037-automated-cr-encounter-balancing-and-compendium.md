---
id: 0037
title: Automated CR Encounter Balancing & redstring Rules Indexing
status: Accepted
created: 2026-09-25
---

# US-0037 — Automated CR Encounter Balancing & redstring Rules Indexing

## User Story

**As an** overworked Dungeon Master prepping weekly combat sessions (Evelyn),  
**I want to** generate mathematically balanced encounters and query canonical rules indexed with `redstring`,  
**So that** combat challenges are fair and exciting while prep time drops from hours to seconds.

## Acceptance Criteria

1. **CR Budget Calculation**: Calculates accurate encounter difficulty thresholds (Easy, Medium, Hard, Deadly) for any party size and level.
2. **redstring BM25 & Semantic Search**: Spells, monster stat blocks, and condition rules are indexed through `redstring` for sub-50ms BM25 and vector queries.
3. **Synergistic Monster Generation**: Proposes enemy combinations with diverse combat roles (brute, artillery, controller).
