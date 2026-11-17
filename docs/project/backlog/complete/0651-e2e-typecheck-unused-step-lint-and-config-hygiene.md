---
id: '0651'
title: E2E Suite Gets a Typecheck Gate, an Unused-Step Check, and Config-Driven Base URLs
status: Complete
created: 2026-11-17
dependencies: []
governing_adrs:
- ADR-0009
- ADR-0010
- ADR-0014
governing_prds: []
governing_stories: []
target_release: 0.9.0
severity: medium
source_audits:
- w2-e2e-bdd.md
---

# TASK-0651: E2E Suite Gets a Typecheck Gate, an Unused-Step Check, and Config-Driven Base URLs

## Status
Complete

## Summary
The Playwright BDD suite has no type gate. Playwright transpiles TypeScript without type checking, so the type error at `e2e/steps/character_sheet_steps.ts:65` passes every current gate. Unused step definitions are also not reported. Two steps hard-code `http://localhost:5173`, which ignores `PLAYWRIGHT_BASE_URL`. The `@serial` tags have no effect. Add a typecheck of `e2e/` to the gates, add an unused-step check, and read the base URL from the config. Remove the dead steps and the dead tags.

## Problem Statement
- `e2e/steps/character_sheet_steps.ts:65` returns `charId` typed `string | null`. Strict TypeScript reports TS2322. No `typecheck` script covers `e2e/`.
- Unused definitions (no feature uses them): `common_steps.ts` `I click the {string} button`, `common_steps.ts` `I should see a toast notification containing {string}`, and `character_sheet_steps.ts:337` `{word} clicks "Save Guardrails"` (the unprefixed form at line 350 is the one in use).
- `e2e/steps/vtt_steps.ts:36` and `:84` hard-code `baseURL: 'http://localhost:5173'`.
- `@serial` tags on all four feature files have no effect. `playwright.config.ts` sets `workers: 1` and the tag is not mapped in `defineBddConfig`.
- `character_sheet_steps.ts:243` uses `waitForTimeout(200)`. Lines 241 and 256 branch on `isVisible()` without waiting.

## Documentation & Architecture Review
- ADR-0009 (ruff and pre-commit) and ADR-0010 (CI pipeline): the typecheck and lint gates belong to the existing `typecheck` and `lint` targets.
- `docs/reference/cli-interfaces.md` lists the test targets. Update it if a target changes.
- `docs/how-to/test-user-flows-with-playwright-bdd.md` describes running the suite. Update the base URL instructions.

## Product & User Story References
Developer tooling. No user story applies (DoR 8 covers user-facing features only). ADR-0014 governs the suite.

## Detailed Specification & Implementation Plan
1. Add `e2e/tsconfig.json` (strict, `noEmit`, types for `@playwright/test` and `playwright-bdd`). Add an `e2e:typecheck` script in `package.json` and call it from the existing `typecheck` target and from `make test-bdd`.
2. Fix the type error at `character_sheet_steps.ts:65` by narrowing `charId` and throwing when it is missing (this matches TASK-0650).
3. Add `scripts/check_e2e_unused_steps.py` (or a Node script under `e2e/scripts/`). It reads step patterns from `e2e/steps` and step lines from `e2e/features`, and fails on any definition with zero matches. Run it from `make test-bdd`. Use `uv run` for any Python.
4. Delete the three unused definitions above, or add the scenario that needs them if the behaviour is still wanted.
5. Replace the two `baseURL` literals with the config value (`test.info().project.use.baseURL` or the shared fixture).
6. Either remove the `@serial` tags, or map them in `defineBddConfig` so that they affect scheduling. Record the choice in the task's Definition of Done.
7. Replace the fixed wait at line 243 with a web-first assertion (`expect(locator).toBeVisible()`). Remove `isVisible()` branches.

## Frontdoor Blackbox Test Plan
This task changes tooling, so no user flow changes. Verification is by gate:
- `make test-bdd` fails when a deliberately wrong type is added to a step file (checked locally, not committed), and passes on the fixed tree.
- `make test-bdd` fails when an unused step is added to a step file (checked locally), and passes on the fixed tree.
- `PLAYWRIGHT_BASE_URL=http://localhost:4173 pnpm exec playwright test --list` shows that the steps use the overridden URL (test by a debug log in a local run only).

## Definition of Done
1. `make test-bdd` runs the typecheck and the unused-step check and passes.
2. `character_sheet_steps.ts:65` compiles under strict mode.
3. No hard-coded `localhost` URL remains in `e2e/steps`.
4. The `@serial` tags are either functional or removed, and the decision is recorded.
5. `make test-e2e` passes in chromium, firefox, and webkit.
6. `docs/reference/cli-interfaces.md` and the how-to reflect the gates.
