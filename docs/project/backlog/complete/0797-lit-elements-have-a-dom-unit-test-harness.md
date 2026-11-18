---
id: '0797'
title: Lit Elements Have a DOM Unit Test Harness
status: Complete
created: 2026-11-17
dependencies: []
governing_adrs:
- ADR-0004
- ADR-0013
governing_prds: []
governing_stories: []
target_bc: frontend
target_release: 0.9.0
---

# TASK-0797: Lit Elements Have a DOM Unit Test Harness

## Status
Complete

## Summary
No package can unit test a Lit element. Node strip-only mode rejects decorators and no DOM is available, so element behaviour (asset image loading, placeholders, permission states) has no unit test. The character card shows no placeholder when a portrait is empty.

## Problem Statement
- `services/*/ui/test/`: tests cover plain modules only.
- `services/character_sheet/ui/src/runefoble-character-card.ts:164`: no placeholder for an empty `portraitUrl`.

## Documentation & Architecture Review
- AGENTS.md hard invariants and DoR 9 (no compatibility shims).
- ADR-0004, ADR-0013.

## Product & User Story References
None. Platform quality work.

## Detailed Specification & Implementation Plan
1. Choose one harness for every UI package (for example `@web/test-runner` with Playwright Chromium, or Vitest with a DOM) and record the choice in `docs/how-to/develop-lit-components-in-storybook.md`. Add it through the pnpm workspace.
2. Add element tests for `AssetImageController` users (blob URL set and revoked) and the App Shell forge permission state.
3. Show `PORTRAIT_PLACEHOLDERS` in the character card for an empty portrait.

## Frontdoor Blackbox Test Plan
- The new element tests run in `pnpm test` for each package and fail when the behaviour is removed.

## Definition of Done
- The test plan passes.
- `uv run pytest`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: medium
- Source audits: `.audit/work/0785.md`, `.audit/work/0788.md` (Discovered)
