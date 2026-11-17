---
id: '0647'
title: Storybook Stories Stop Requesting Missing Portrait SVG Assets
status: Refined
created: 2026-11-17
dependencies:
- TASK-0642
governing_adrs:
- ADR-0004
governing_prds:
- PRD-0013
governing_stories:
- US-0004
- US-0055
target_release: 0.9.0
severity: medium
source_audits:
- w2-app-shell.md
---

# TASK-0647: Storybook Stories Stop Requesting Missing Portrait SVG Assets

## Status
Refined

## Summary
Eight Storybook stories request `/assets/portraits/{fighter,wizard,cleric,rogue}.svg`. None of those files exists in the repository, so the stories log 404 errors. AGENTS.md DoD 3 requires zero console errors in Storybook. Ship real portrait assets, or point the stories at assets that exist. Also remove the App Shell placeholder reference to `fighter.svg` once TASK-0642 has landed.

## Problem Statement
- `w2-app-shell.md` F10: the headless scan of 315 stories found 8 stories with console 404 errors. They are `charactersheet-characterroster--populated-roster`, `charactersheet-characterroster--filtered-assigned`, `charactersheet-characterroster--filtered-unassigned`, `charactersheet-characterbuildermodal--modal-open`, `charactersheet-characterbuildermodal--prepopulated-modal`, `gamesession-sessionlobby--player-view-ready`, `gamesession-sessionlobby--dm-view-all-ready`, and `gamesession-sessionlobby--dm-view-with-absent-stand-in`.
- `frontend/src/runefoble-app.ts:182` pointed at the same missing file (fixed by TASK-0642).
- `find . -name fighter.svg` returns nothing in the repository.

## Documentation & Architecture Review
- ADR-0004 and `docs/how-to/develop-lit-components-in-storybook.md`: stories must render with zero console errors. Document where portrait assets live.
- `docs/reference/design-tokens-and-themes.md`: assets follow the Bauhaus geometric style. The new assets must match.
- `docs/project/backlog/` TASK-0445 (portrait sync) is related. This task only provides the static assets and the story references. It does not add dynamic portraits.

## Product & User Story References
- [`us-0055-dynamic-character-wardrobe-and-condition-portraits.md`](../../user_stories/accepted/us-0055-dynamic-character-wardrobe-and-condition-portraits.md)
- [`us-0004-developer-tests-component-in-storybook.md`](../../user_stories/accepted/us-0004-developer-tests-component-in-storybook.md)

## Detailed Specification & Implementation Plan
1. Create four Bauhaus-style SVG portraits under `frontend/public/assets/portraits/` (`fighter.svg`, `wizard.svg`, `cleric.svg`, `rogue.svg`). Each is under 4 KB and uses only design tokens for colour.
2. Alternatively (decide at refinement, record the choice in the task file), point the stories at a single existing asset and remove the four classes. Pick one approach. Do not keep both.
3. Add a Storybook check to `frontend/` that fails the build if a story requests a `/assets/` path that is not under `frontend/public/`. Implement it as a small Node script run by `pnpm run lint`.
4. Confirm the eight story ids render with zero console errors.

## Frontdoor Blackbox Test Plan
- A headless Storybook run (`pnpm storybook build` then a Playwright script in `frontend/tests/storybook-console.spec.ts`) loads each story id listed above and asserts no console error. Before the fix the eight stories FAIL. After the fix they PASS.
- The check is a Storybook frontdoor (rendered story), not a unit test of an internal class.
- Playwright BDD scenario is not required for this task because it is not a user flow (DoR 8 applies to user-facing features).

## Definition of Done
1. The eight listed stories load with zero console errors.
2. The lint check for `/assets/` references passes.
3. The four portrait assets, or the replacement references, are committed and documented in `docs/how-to/develop-lit-components-in-storybook.md`.
4. `pnpm run build` and `pnpm storybook build` pass.
5. Each new file is under 500 lines (SVGs are under 4 KB).
