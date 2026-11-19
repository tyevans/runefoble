---
id: '0904'
title: "Lit Template Audit: Attribute Names and SVG Templates, With a Lint Check"
status: Refined
created: 2026-11-19
dependencies:
- '0903'
governing_adrs:
- ADR-0004
- ADR-0013
governing_prds: []
governing_stories: []
target_bc: frontend
target_release: 0.9.0
---

# TASK-0904: Lit Template Audit: Attribute Names and SVG Templates, With a Lint Check

## Status

Refined.

## Summary

Two classes of Lit defects hide in the UI packages. A camelCase `@property` without `attribute:` does not react to a kebab-case attribute that a parent sets (TASK-0903). SVG children written with the `html` tag do not render (the atlas pins). Find every case and add a check so new cases fail the build.

## Problem Statement

- Atlas pins: the pin layer uses the `html` tag for `<g>`/`<text>` children, so the pins are hidden (triage group D; `campaign_analytics_and_codex.feature` "pin is listed").
- Forge elements: TASK-0903.

## Documentation & Architecture Review

- `.audit/reports/e2e-triage-1.md` gives the evidence (gateway log lines, error-context files).
- ADR-0014: user flows are verified through Playwright without backdoors or `page.route` fakes of our own services. ADR-0015: no invented values and no success shown after an error.

## Product & User Story References

None beyond the scenarios named below.

## Detailed Specification & Implementation Plan

1. Scan all `services/*/ui/src` and `frontend/src` for camelCase `@property` declarations without `attribute:` that any template or test sets as a kebab-case attribute. Fix each one.
2. Fix every SVG fragment that uses `html` instead of `svg` (the atlas pin layer first).
3. Add a check (a small script in `scripts/` run by `make lint`, or an ESLint rule if the repo has ESLint) that fails on a kebab-case attribute bound to an element whose property has no matching `attribute:`. Document it in `docs/how-to/develop-lit-components-in-storybook.md`.

## Frontdoor Blackbox Test Plan

- DOM test: an atlas pin renders an SVG `text` element with the pin label.
- The new check fails on a sample with a missing `attribute:` (test on a fixture, not on the real tree).
- Playwright on Kind (orchestrator): `campaign_analytics_and_codex.feature` pin scenario.

## Definition of Done

- The plan is done and the tests pass. The orchestrator runs the named Playwright scenarios on Kind. Docs and CHANGELOG updated.

## Audit Provenance

- Severity: medium
- Source audits: .audit/reports/e2e-triage-1.md
