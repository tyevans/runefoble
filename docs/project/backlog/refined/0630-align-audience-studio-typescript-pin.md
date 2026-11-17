---
id: '0630'
title: Align audience_studio TypeScript Pins with the Workspace Version
status: Refined
created: 2026-11-17
dependencies: []
governing_adrs:
- ADR-0004
governing_prds: []
governing_stories: []
target_release: 0.9.0
severity: low
source_audits:
- w1-gates-frontend.md
- w2-audience-studio.md
---

# TASK-0630: Align audience_studio TypeScript Pins with the Workspace Version

## Status
Refined

## Summary
Eleven workspace packages pin `typescript` to `~7.0.2`. The two audience-studio packages pin `~5.7.3`, so the pnpm workspace compiles under two TypeScript majors. Move both to `~7.0.2`, regenerate the lockfile, and prove the builds still pass.

## Problem Statement
- `services/audience_studio/package.json:26` and `services/audience_studio/ui/package.json:21` pin `~5.7.3` (`w1-gates-frontend.md` F2, `w2-audience-studio.md` F11).
- `frontend/package.json:32` and the other UI packages pin `~7.0.2`.
- TASK-0439 and TASK-0499 touch the same packages but do not change the TypeScript version.

## Documentation & Architecture Review
- ADR-0004: UI and service packages build through the same workspace toolchain.
- Record the pin in `docs/how-to/develop-lit-components-in-storybook.md` only if it names a version (check first).

## Product & User Story References
- None.

## Detailed Specification & Implementation Plan
1. Set both audience-studio `typescript` pins to `~7.0.2`.
2. Run `pnpm install` at repo root; commit `pnpm-lock.yaml`.
3. Run `pnpm -r run typecheck`, `pnpm run build` and `services/audience_studio` build.
4. Fix any new type errors in audience-studio source without changing behaviour.

## Frontdoor Blackbox Test Plan
- Before fix: `pnpm -r exec -- tsc --version` reports two majors across the workspace.
- After fix: one major across the workspace; `pnpm -r run typecheck` and `pnpm run build` exit 0; the audience blackbox suite (`tests/test_blackbox_audience_studio.py`) passes.

## Definition of Done
1. One TypeScript version across the workspace.
2. Lockfile updated.
3. Typecheck and build gates pass.
4. No file above 500 lines.
