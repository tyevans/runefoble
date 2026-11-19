---
id: '0650'
title: E2E Steps Fail Loudly Without Fallback IDs and Use Precise Selectors and Assertions
status: Complete
created: 2026-11-17
dependencies:
- TASK-0649
governing_adrs:
- ADR-0014
governing_prds:
- PRD-0023
governing_stories:
- US-0063
- US-0065
- US-0069
target_release: 0.9.0
---

# TASK-0650: E2E Steps Fail Loudly Without Fallback IDs and Use Precise Selectors and Assertions

## Status
Complete

## Summary
Setup steps fall back to fixed identifiers when an API call fails (`'4'`, `'char-valeros'`, the title "Tomb of the Star-Eater"). A failed precondition then lets the scenario run on an entity that may not exist. Some selectors pick the first matching element, and one clipboard assertion skips its check when the clipboard is empty. Remove each fallback. Make each selector target the element named in the feature text. Make each assertion fail when its precondition is missing.

## Problem Statement
- `e2e/steps/campaign_hub_steps.ts:37-39` and `:41`: campaign id `'4'` on error or with no token.
- `campaign_hub_steps.ts:147-149`: campaign id `'4'` and title "Tomb of the Star-Eater".
- `e2e/steps/character_sheet_steps.ts:56-58`: `charId = 'char-valeros'` when creation fails.
- `e2e/steps/vtt_steps.ts:96-103`: if Sarah's card is not visible, the step ticks the first `.checkbox-absent` in the lobby, which can belong to another player. Line 49 (`world.getPage('valeros') || world.getPage('evelyn')!`) hides a missing Valeros context.
- `character_sheet_steps.ts:326-331`: the feature says `checks "Avoid Melee"`. The step looks for `Avoid Frontline Melee` and falls back to the first checkbox. The component text is in `services/character_sheet/ui/src/runefoble-stand-in-guardrails.templates.ts:75`.
- `campaign_hub_steps.ts:343-356`: `if (clipboardText)` skips the comparison when the clipboard read returns null.
- `character_sheet_steps.ts:198-208`: the HP step ignores `_fromHp` and checks only the final value.

## Documentation & Architecture Review
- ADR-0014: a precondition failure fails the scenario. There is no "continue anyway" path.
- `docs/how-to/test-user-flows-with-playwright-bdd.md` must state the rule: setup throws on failure, selectors name the labelled element.

## Product & User Story References
- [`us-0063-campaign-creation-dashboard-and-zanzibar-roles.md`](../../user_stories/accepted/us-0063-campaign-creation-dashboard-and-zanzibar-roles.md)
- [`us-0069-character-sheet-inspector-and-active-session-binding.md`](../../user_stories/accepted/us-0069-character-sheet-inspector-and-active-session-binding.md)
- [`us-0025-personalized-ai-stand-in-tactical-policies.md`](../../user_stories/accepted/us-0025-personalized-ai-stand-in-tactical-policies.md)

## Detailed Specification & Implementation Plan
1. Delete every fallback id and title literal in `e2e/steps`. Replace with the value returned by the setup call, stored in the scenario world object. If the setup call fails, the step throws with the response body.
2. Replace "first matching element" selectors with a locator scoped to the participant card or the toggle label named in the feature text. Use `getByRole('checkbox', { name: 'Avoid Melee' })`, and fail if the count is not one.
3. Remove the `world.getPage('valeros') || world.getPage('evelyn')!` fallback. Missing contexts throw.
4. Clipboard: grant the `clipboard-read` permission in the fixture. Assert `readText()` equals the input value. A null result fails the step.
5. HP step: read the starting HP from the public character record in setup, then assert the change from that value.
6. Keep each file under 500 lines. Use the decomposed files from TASK-0512 and TASK-0447.

## Frontdoor Blackbox Test Plan
These are regression checks on the existing scenarios, with stricter assertions:
- `character_sheet.feature`: "Stand-in guardrail 'Avoid Melee' is saved" passes only when the toggle with the exact label is checked, and fails when the label is absent (verified with a temporary local feature edit, not committed).
- `campaign_hub.feature`: "copies the valid join URL to the clipboard" asserts clipboard equality.
- `session_lobby_and_vtt.feature`: Sarah's absent checkbox scenario fails if Sarah's card is removed.
- A new negative check in `e2e/support/guards.test.ts` (removed). It moved to `e2e/unit/guards.test.ts`. (unit): the fallback helper throws when the setup response is not OK.

## Definition of Done
1. `grep -rn "Tomb of the Star-Eater\|'char-valeros'\|campaignId = '4'\|first matching\|if (clipboardText)" e2e/steps` returns no match.
2. Every listed scenario passes in all three browsers.
3. No `.first()` or `.nth(0)` selector remains in `e2e/steps` without a justification comment.
4. Each file is under 500 lines.
5. The how-to states the fail-loud rule with one example.

## Orchestrator Addenda (2026-11-17)

Source: `.audit/synth/discovered-round1.md`.

- The gateway-unavailable scenario needs a public make target that stops and starts the gateway. Add the target or drop the scenario.

## Audit Provenance

- Severity: high
- Source audits: `w2-e2e-bdd.md`
