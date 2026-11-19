---
id: '0763'
title: Hex Colour Lint Gate With Baseline and Token Migration of The Watcher Styles
status: Complete
created: 2026-11-17
dependencies: []
governing_adrs:
- ADR-0012
- ADR-0004
governing_prds:
- PRD-0013
governing_stories:
- US-0016
target_bc: the_watcher
target_release: 0.9.0
---
# TASK-0763: Hex Colour Lint Gate With Baseline and Token Migration of The Watcher Styles

## Status
Complete

## Summary
UI styles hold about 2,200 hex values; about 719 are not inside a `var(--...)` fallback. Add a lint gate that blocks new hex literals. Record the current count as a baseline that can only fall. Migrate the worst file group (The Watcher) as the first slice.

## Problem Statement
- `services/the_watcher/ui/src/runefoble-faction-radar.styles.ts` holds 81 hex values.
- Other large files (follow-up tasks, one per service): `frontend/src/components/minigames/runefoble-minigame-roulette.ts` (62), `services/game_session/ui/src/runefoble-campfire-crafting.styles.ts` (59), `services/campaign_lore/ui/src/runefoble-campaign-atlas.styles.ts` (57), `services/game_session/ui/src/runefoble-tavern-parlor.styles.ts` (56).
- Inline hex in templates, for example `services/rules_compendium/ui/src/runefoble-homebrew-creator.ts:132`.

## Documentation & Architecture Review
- ADR-0012, ADR-0004, `docs/reference/design-tokens-and-themes.md`. Add a token for any missing semantic colour in the theme files, not in components. TASK-0647 covers only one portrait SVG.

## Product & User Story References
- PRD-0013. US-0016 (themable frontend).

## Detailed Specification & Implementation Plan
1. Add a script `scripts/check_hex_literals.py` (run by `make lint`). It fails when a hex literal appears outside token definition files, and when the count exceeds `scripts/hex_baseline.json`. The baseline is per file.
2. Migrate every hex value in `services/the_watcher/ui/src/*.styles.ts` and templates to `var(--rf-*)`. Lower the baseline.
3. Check light and dark contrast with `frontend/src/stories/theme-contrast-matrix.stories.ts`.
4. File one follow-up per remaining service after this task lands.

## Frontdoor Blackbox Test Plan
- The lint script runs against a temporary file with a new hex literal and exits non-zero (public CLI test).
- Storybook: each changed Watcher component in light and dark theme, zero console errors.

## Definition of Done
- Gate in `make lint` and CI. Baseline file present. Watcher styles have no unwrapped hex.
- `docs/reference/design-tokens-and-themes.md` describes the gate. Gates pass. No file over 500 lines.

## Audit Provenance
- Severity: low
- Source audits: `frontend-ui`
