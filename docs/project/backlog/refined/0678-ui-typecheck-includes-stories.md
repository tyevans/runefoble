---
id: '0678'
title: Microfrontend Package Typecheck Includes Storybook Stories
status: Refined
created: 2026-11-17
dependencies: []
governing_adrs:
- ADR-0004
- ADR-0009
- ADR-0010
governing_prds:
- PRD-0013
governing_stories:
- US-0004
target_release: 0.9.0
severity: low
source_audits:
- work/0613.md
---

# TASK-0678: Microfrontend Package Typecheck Includes Storybook Stories

## Status
Refined. Created from the discovered-defect triage of round 1 (2026-11-17).

## Summary
All 11 UI packages under `services/*/ui/` exclude `src/**/*.stories.ts` from their `tsconfig.json`. A type error in a story passes the package typecheck. This task includes stories in the typecheck and fixes any errors found.

## Problem Statement
- Each `services/<bc>/ui/tsconfig.json` (11 files) has `"exclude": ["src/**/*.stories.ts"]`.
- Story files have no type gate. Storybook builds with esbuild and does not type-check.
- The asset-forge work (TASK-0613) shows story props can drift from component APIs.

## Documentation & Architecture Review
- ADR-0004: stories are part of the component contract.
- ADR-0010: the typecheck belongs in the CI pipeline. Keep the existing `typecheck` script name.
- `docs/how-to/develop-lit-components-in-storybook.md`: note that stories are type-checked.

## Product & User Story References
- PRD-0013 and US-0004: developers test components in Storybook. Story types must match the component.

## Detailed Specification & Implementation Plan
1. In each of the 11 `tsconfig.json` files, remove the `exclude` entry for stories. Keep `src` in `include`.
2. Run `pnpm run typecheck` in each package. Fix the story type errors in the story files only. Do not change component APIs to satisfy stories.
3. If a story fix needs a component API change, stop and split that package into its own task.
4. Update the how-to note.

## Frontdoor Blackbox Test Plan
- Gate test: add a temporary story with a wrong prop type in one package. `pnpm run typecheck` exits non-zero. Remove the temporary story. The check is run once in a script, not kept in the suite.
- After the fixes, every package `pnpm run typecheck` exits 0.
- Storybook build for each package has zero console errors (existing gate).

## Definition of Done
- Tests above pass. No story is excluded in any `services/*/ui/tsconfig.json`.
- Changed files under 500 lines. `make lint` and `pnpm run build` pass.
- If more than 3 story files need edits, split the work per package and record it in this file.
