---
id: '0271'
title: Frontend App Data Service Fixtures and Client Modular Decomposition
status: Proposed
created: 2026-09-27
dependencies: []
governing_adrs:
- ADR-0004
- ADR-0007
governing_prds: []
governing_stories: []
target_release: 0.8.0
---

# TASK-0271: Frontend App Data Service Fixtures and Client Modular Decomposition

## Status
Proposed

## Summary
Decompose `frontend/src/services/app-data-service.ts` (354 lines, 70.8% of limit) by extracting static fallback fixtures (`FALLBACK_CAMPAIGNS`, `FALLBACK_CHARACTERS`, `FALLBACK_PARTICIPANTS`, `FALLBACK_SESSIONS`) into a dedicated fixture module `frontend/src/services/app-data-service.fixtures.ts`, keeping `AppDataService` focused strictly on HTTP API client calls and state orchestration (< 220 lines).

## Problem Statement
`frontend/src/services/app-data-service.ts` currently mixes heavy static fixture definitions (campaigns, character stats, party members, session lists) with live Gateway API network client logic. As additional character attributes, inventory items, and settlement endpoints are added in upcoming milestones, this file will rapidly exceed the 500-line limit.

## Governing Architecture & ADRs
- **ADR-0004: Lit Web Components and Storybook UI**: Modular test fixtures and fallback data.
- **ADR-0007: Domain-Driven Design Architecture**: Separation of static test fixtures from runtime data transport.

## Scope of Work
1. **Fixture Extraction (`frontend/src/services/app-data-service.fixtures.ts`)**:
   - Extract `FALLBACK_CAMPAIGNS`, `FALLBACK_CHARACTERS`, `FALLBACK_MEMBERS`, `FALLBACK_PARTICIPANTS`, and `FALLBACK_SESSIONS` (< 150 lines).
2. **Service Modularization (`frontend/src/services/app-data-service.ts`)**:
   - Import fallback constants from `.fixtures.ts`.
   - Keep `AppDataService` methods strictly focused on HTTP fetching, JSON deserialization, auth header propagation, and offline fallback (< 220 lines).
3. **Verification**:
   - Verify frontend tests and Storybook fixtures continue to load identical fallback data.

## Definition of Done
- `frontend/src/services/app-data-service.ts` reduced to < 220 lines.
- Extracted `frontend/src/services/app-data-service.fixtures.ts` strictly < 160 lines.
- All frontend tests and Storybook stories pass without regression.
- Code passes lint and typecheck.
