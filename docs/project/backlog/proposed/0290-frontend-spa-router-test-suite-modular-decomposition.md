---
id: '0290'
title: Frontend SPA Router Test Suite Modular Decomposition
status: Proposed
created: 2026-09-28
dependencies:
- TASK-0206
- TASK-0247
governing_adrs:
- ADR-0004
- ADR-0012
- ADR-0013
governing_prds:
- PRD-0023
governing_stories:
- US-0066
target_release: 0.8.0
---

# TASK-0290: Frontend SPA Router Test Suite Modular Decomposition

## Status
Proposed

## Summary
Decompose `frontend/test/router.test.ts` (312 lines, 62.4% of limit) into modular TypeScript test submodules under `frontend/test/router/` (`patterns.test.ts`, `guards.test.ts`, `proxy.test.ts`, `title-resolver.test.ts`), ensuring all test modules remain strictly < 110 lines per Hard Invariant 6.

## Problem Statement
`frontend/test/router.test.ts` tests standard client route pattern matching, parameter extraction, query string parsing, navigation events, route authentication guards, teardown lifecycle callbacks, Vite proxy configuration, and asynchronous route title resolution with caching in a single monolithic test file. As new deep links (such as settlement establishments, minigames, and codex entries) are added to the SPA router, this file will rapidly approach the 500-line invariant limit unless partitioned into focused, single-responsibility submodules.

## Governing Architecture & ADRs
- **ADR-0004: Lit Web Components and Storybook UI**: Client-side single-page application navigation and reactive rendering.
- **ADR-0012: Design System Theming and Bauhaus Modernism**: Dynamic breadcrumb updates and route titles.
- **ADR-0013: Frontend Microfrontend Architecture**: Decoupled view composition and route-bound lifecycle.

## Scope of Work
1. **Pattern Matching & Parameter Tests (`frontend/test/router/patterns.test.ts`)**:
   - Extract standard route declarations, static route matches, campaign/lobby/character parameter extraction, query parsing, and fallback breadcrumb generation (< 110 lines).
2. **Navigation Guards & Teardown Tests (`frontend/test/router/guards.test.ts`)**:
   - Extract route change listener notifications, boolean navigation guard abortion, unauthenticated redirect handling, and cleanup/teardown hook execution (< 100 lines).
3. **Vite Proxy Configuration Tests (`frontend/test/router/proxy.test.ts`)**:
   - Extract reverse proxy configuration tests for `/api/v1` and WebSocket proxy mapping for `/ws` (< 70 lines).
4. **Dynamic Title Resolution & Caching Tests (`frontend/test/router/title-resolver.test.ts`)**:
   - Extract asynchronous title resolution, synchronous caching verification, default identifier formatting fallback, and character sheet breadcrumb naming (< 110 lines).
5. **Verification**:
   - Safely remove monolithic `frontend/test/router.test.ts` and ensure `npm test` runs all submodules with 100% passing rate.

## Definition of Done
- `frontend/test/router.test.ts` decomposed into `frontend/test/router/` suite.
- All extracted test submodules strictly < 110 lines per Hard Invariant 6.
- 100% test passing via `npm test` in `frontend/`.
- Monolithic `frontend/test/router.test.ts` safely removed.
