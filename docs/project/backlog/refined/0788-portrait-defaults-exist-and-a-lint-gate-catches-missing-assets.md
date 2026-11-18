---
id: '0788'
title: Portrait Defaults Point at Real Images and a Lint Gate Catches Missing Asset Paths
status: Refined
created: 2026-11-17
dependencies: []
governing_adrs:
- ADR-0004
- ADR-0013
governing_prds: []
governing_stories: []
target_bc: character_sheet
target_release: 0.9.0
---

# TASK-0788: Portrait Defaults Point at Real Images and a Lint Gate Catches Missing Asset Paths

## Status
Refined. Found during batch 23 integration, 2026-11-17.

## Summary
TASK-0647 fixed the stories, but code and fixtures still default to portrait files that do not exist. No lint step catches a missing `/assets/` path.

## Problem Statement
- `services/character_sheet/ui/src/roster/runefoble-character-roster.ts:90`: `/assets/portraits/default.svg`.
- `services/character_sheet/ui/src/runefoble-wardrobe-gallery.ts:22-23`.
- `frontend/src/fixtures/app-data-service.fixtures.ts:25-27` and `frontend/test/*.test.ts`.
- `services/character_sheet/src/character_sheet/portrait.py:57,165` and `models/character.py:42-43,92`.

## Documentation & Architecture Review
- AGENTS.md hard invariants and DoR 9 (no compatibility shims).
- ADR-0004, ADR-0013.

## Product & User Story References
None. Platform quality work.

## Detailed Specification & Implementation Plan
1. Use `PORTRAIT_PLACEHOLDERS` from `@runefoble/ui-core` in the UI and fixtures.
2. Character sheet answers with no portrait URL when none is set (null), and the UI shows the placeholder. Do not return a path to a file that does not exist.
3. Add a lint step to `pnpm run lint` that fails on an `/assets/` path that no package serves.

## Frontdoor Blackbox Test Plan
- A character created with no portrait answers `portrait_url: null` through the public route.
- The lint step fails on a planted missing path and passes on main.

## Definition of Done
- The test plan passes.
- `uv run pytest`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: low
- Source audits: `.audit/work/0647.md` (Discovered, spec step 3)
