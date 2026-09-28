---
id: '0329'
title: Board Templates Test Suite Modular Decomposition
status: Proposed
created: 2026-09-28
dependencies:
- TASK-0192
governing_adrs:
- ADR-0004
- ADR-0012
- ADR-0013
governing_prds:
- PRD-0013
governing_stories:
- US-0043
target_release: 0.8.0
---

# TASK-0329: Board Templates Test Suite Modular Decomposition

## Status
Proposed

## Summary
Decompose `frontend/test/board-templates.test.ts` (275 lines, 55.0% of limit) into modular sub-suites under `frontend/test/board_templates/` (`kinematics.test.ts`, `cell.test.ts`, and `overlays.test.ts`) with an aggregator entry point, keeping all test files strictly < 110 lines per Hard Invariant 6.

## Problem Statement
`frontend/test/board-templates.test.ts` verifies kinematics templates, health bar color thresholds, board cell rendering, and radial menu / AoE overlays within a single test file. As new board interaction templates and tactical overlays are added, this test suite will approach the 500-line limit unless decomposed into focused test suites.

## Governing Architecture & ADRs
- **ADR-0004: Bauhaus Microfrontend Design System**: Design token and Lit template verification.
- **ADR-0012: Theming System and Contrast Invariants**: Color tokens and CSS variable assertions.
- **ADR-0013: Modular Decomposition**: All source and test files kept strictly < 500 lines (sub-suites < 110 lines).

## Scope of Work
1. **Kinematics Submodule Tests (`frontend/test/board_templates/kinematics.test.ts`)**:
   - Extract health bar color calculations, distance ruler vectors, and ghost banner template assertions (< 90 lines).
2. **Board Cell Template Tests (`frontend/test/board_templates/cell.test.ts`)**:
   - Extract board cell rendering, token placement, and terrain hazard visual test cases (< 90 lines).
3. **Overlays Template Tests (`frontend/test/board_templates/overlays.test.ts`)**:
   - Extract radial menu overlay, AoE template rendering, and status bar banner tests (< 100 lines).
4. **Aggregator Entry Point (`frontend/test/board-templates.test.ts`)**:
   - Re-export and execute sub-suites to preserve CI test runner discovery (< 30 lines).
5. **Verification**:
   - Execute `npm test` in `frontend/` to ensure 100% test pass rate.

## Definition of Done
- `board-templates.test.ts` decomposed into modular sub-suites under `frontend/test/board_templates/`.
- All created and modified files strictly < 110 lines each per Hard Invariant 6.
- Frontend test runner executes all board template test suites with zero failures.
