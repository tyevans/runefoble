---
id: '0347'
title: App Shell Views Wiring Audit Test Suite Modular Decomposition
status: Proposed
created: 2026-09-28
dependencies:
- TASK-0251
governing_adrs:
- ADR-0004
- ADR-0010
- ADR-0012
- ADR-0013
governing_prds:
- PRD-0023
governing_stories:
- US-0068
target_release: 0.8.0
---

# TASK-0347: App Shell Views Wiring Audit Test Suite Modular Decomposition

## Status
Proposed

## Summary
Decompose `frontend/test/app-shell-views-wiring-audit.test.ts` (278 lines, 55.6% of limit) into modular test sub-suites under `frontend/test/wiring_audit/` (`route-matrix.test.ts`, `manifest-validation.test.ts`, `lifecycle-and-breadcrumbs.test.ts`) with an aggregator entry point, keeping all test files strictly < 110 lines per Hard Invariant 6.

## Problem Statement
`frontend/test/app-shell-views-wiring-audit.test.ts` tests route pattern matching across 10 distinct application paths, validates the component manifest for all active views, verifies route-bound WebSocket lifecycle requirements, and tests breadcrumbs/fallback routes within a single 278-line test file. As new settlement views, mobile tavern routes, and modder plugin views are added, this test suite will approach the 500-line limit unless decomposed into focused test suites.

## Governing Architecture & ADRs
- **ADR-0004: Frontend Application Shell**: Deep route-aware UI orchestration.
- **ADR-0010: Continuous Integration Pipeline**: Rapid and modular test suite execution.
- **ADR-0013: Modular Decomposition**: All source files kept strictly < 500 lines (submodules < 110 lines).

## Scope of Work
1. **Shared Route Fixtures (`frontend/test/wiring_audit/fixtures.ts`)**:
   - Extract `ROUTE_MATRIX`, `VIEW_COMPONENT_MANIFEST`, and helper resolvers (< 60 lines).
2. **Route Pattern & Param Extraction Tests (`frontend/test/wiring_audit/route-matrix.test.ts`)**:
   - Extract parameterized route matching, view resolution, and parameter extraction tests (< 85 lines).
3. **Component Manifest Validation Tests (`frontend/test/wiring_audit/manifest-validation.test.ts`)**:
   - Extract active view component manifest verification and custom element registration tests (< 80 lines).
4. **Lifecycle & Breadcrumb Tests (`frontend/test/wiring_audit/lifecycle-and-breadcrumbs.test.ts`)**:
   - Extract route-bound WebSocket socket teardown, dynamic breadcrumbs, and fallback redirects (< 85 lines).
5. **Aggregator Entry Point (`frontend/test/app-shell-views-wiring-audit.test.ts`)**:
   - Re-export test suites to preserve standard npm test execution (< 25 lines).
6. **Verification**:
   - Ensure `npm run test` in `frontend/` passes 100%.

## Definition of Done
- `frontend/test/wiring_audit/` sub-suites strictly < 110 lines each per Hard Invariant 6.
- Root `app-shell-views-wiring-audit.test.ts` reduced to < 30 lines.
- Passes all frontend tests via `npm run test` in `frontend/`.
- Code passes lint and format checks.
