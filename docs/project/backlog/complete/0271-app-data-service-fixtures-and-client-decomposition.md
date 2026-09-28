---
id: '0271'
title: Frontend App Data Service Fixtures and Client Modular Decomposition
status: Complete
created: 2026-09-27
dependencies: []
governing_adrs:
- ADR-0004
- ADR-0007
governing_prds: []
governing_stories: []
target_release: 0.8.0
pr_url: https://github.com/tyevans/runefoble/pull/303
---
# TASK-0271: Frontend App Data Service Fixtures and Client Modular Decomposition

## Status
Refined

## Summary
Decompose `frontend/src/services/app-data-service.ts` (400 lines, 80.0% of limit) by extracting static fallback fixtures (`FALLBACK_CAMPAIGNS`, `FALLBACK_CHARACTERS`, `FALLBACK_MEMBERS`, `FALLBACK_PARTICIPANTS`, `FALLBACK_SESSIONS`) into a dedicated fixture module `frontend/src/services/app-data-service.fixtures.ts`, keeping `AppDataService` focused strictly on HTTP API client calls and state orchestration (< 220 lines).

## Problem Statement
`frontend/src/services/app-data-service.ts` currently reaches 400 lines, mixing heavy static fixture definitions (campaigns, character stats, party members, session lists) with live Gateway API network client logic. As additional character attributes, inventory items, and settlement endpoints are added in upcoming milestones, this file will rapidly exceed the 500-line invariant limit unless decoupled.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/how-to/navigate-client-spa-routes-and-breadcrumbs.md`: Client app service data fetching.
  - `docs/how-to/manage-campaign-lifecycle-and-invites.md`: Campaign and member fixture data structures.
- **Governing Architecture & ADRs**:
  - **ADR-0004: Lit Web Components and Storybook UI**: Modular test fixtures and offline fallback data.
  - **ADR-0007: Domain-Driven Design Architecture**: Clean separation between static fixtures and runtime HTTP communication.

## Product & User Story References
- Technical debt refactoring supporting:
  - [`prd-0023-unified-frontend-application-shell-and-campaign-hub.md`](../../product/accepted/prd-0023-unified-frontend-application-shell-and-campaign-hub.md)
  - [`us-0063-campaign-creation-and-shareable-invite-links.md`](../../user_stories/accepted/us-0063-campaign-creation-and-shareable-invite-links.md)
  - [`us-0064-character-roster-management-and-party-assignment.md`](../../user_stories/accepted/us-0064-character-roster-management-and-party-assignment.md)

## Detailed Specification & Implementation Plan
1. **Fixture Extraction (`frontend/src/services/app-data-service.fixtures.ts`)**:
   - Extract `FALLBACK_CAMPAIGNS`, `FALLBACK_CHARACTERS`, `FALLBACK_MEMBERS`, `FALLBACK_PARTICIPANTS`, and `FALLBACK_SESSIONS` (< 150 lines).
2. **Service Modularization (`frontend/src/services/app-data-service.ts`)**:
   - Import fallback constants from `.fixtures.ts`.
   - Keep `AppDataService` methods strictly focused on HTTP fetching, JSON deserialization, auth header propagation, and offline fallback (< 220 lines).
3. **Verification**:
   - Verify frontend tests and Storybook fixtures continue to load identical fallback data.

## INVEST Criteria Evaluation
- **Independent (I)**: Pure internal refactoring of `app-data-service.ts` without public API changes.
- **Negotiable (N)**: Structure of fixture groupings can be customized.
- **Valuable (V)**: Protects core frontend data service from exceeding the 500-line invariant limit.
- **Estimable (E)**: Clear, straightforward file extraction.
- **Small (S)**: Target files are each well under 250 lines.
- **Testable (T)**: Existing blackbox frontend tests immediately verify zero regressions.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. `frontend/src/services/app-data-service.ts` reduced to < 220 lines.
2. Extracted `frontend/src/services/app-data-service.fixtures.ts` strictly < 160 lines.
3. All frontend tests (`pnpm test`) and Storybook stories pass without regression.
4. Code passes lint and typecheck (`pnpm run lint` and `pnpm run build`).
