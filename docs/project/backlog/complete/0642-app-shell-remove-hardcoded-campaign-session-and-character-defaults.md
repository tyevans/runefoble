---
id: '0642'
title: App Shell Derives Campaign, Session, and Character State From Routes and API Data
status: Complete
created: 2026-11-17
dependencies:
- TASK-0640
governing_adrs:
- ADR-0004
- ADR-0007
- ADR-0013
governing_prds:
- PRD-0023
governing_stories:
- US-0066
- US-0069
target_release: 0.9.0
severity: medium
source_audits:
- w2-app-shell.md
---

# TASK-0642: App Shell Derives Campaign, Session, and Character State From Routes and API Data

## Status
Complete

## Summary
`runefoble-app.ts` and two child components contain fixed identifiers, titles, and invented stats. Examples are campaign `'4'`, session `'session-tomb-14'`, the placeholder character "Adventurer", and the stat values `currentHp: 30` and `armorClass: 14`. The campaign switcher shows two fixed campaigns. Remove all of them. The active campaign and session come from the route. The switcher and the character views come from the API. When no data exists, the view shows an empty state.

## Problem Statement
- `frontend/src/runefoble-app.ts:24` sets `campaignId = '4'`. Line 25 sets `sessionId = 'session-tomb-14'`. Lines 26-27 set the titles "Tomb of the Star-Eater" and "Session #14".
- `frontend/src/runefoble-app.ts:30` and `:66` set the default user `user-valeros`.
- `frontend/src/runefoble-app.ts:79` maps campaign ids `'4'` and `'5'` to fixed names.
- `frontend/src/runefoble-app.ts:182` `resolveActiveCharacter()` returns `char-placeholder` named "Adventurer" with `/assets/portraits/fighter.svg`.
- `frontend/src/runefoble-app.ts:186-200` `handleSelectCharacter()` invents `currentHp: 30` and `armorClass: 14`.
- The character sheet branch uses the defaults `['Marcus']` for guardrails, `{3: 1}` for spell slots, and the priority "Save Level 3 slots for Revivify".
- `frontend/src/components/runefoble-campaign-nav.ts:14-17` defaults `availableCampaigns` to two fixed campaigns. The header never passes live campaigns.
- `frontend/src/components/runefoble-user-profile.ts:94-110` falls back to a profile for "Valeros".

## Documentation & Architecture Review
- `docs/how-to/navigate-client-spa-routes-and-breadcrumbs.md` describes route parameters. Its examples must use route parameters, not fixed ids.
- DoR 9: no default values that keep fixture behaviour in production.
- ADR-0013: the character sheet UI stays in `services/character_sheet/ui`. The App Shell passes data only.

## Product & User Story References
- [`us-0066-client-side-routing-navigation-and-breadcrumbs.md`](../../user_stories/accepted/us-0066-client-side-routing-navigation-and-breadcrumbs.md)
- [`us-0069-character-sheet-inspector-and-active-session-binding.md`](../../user_stories/accepted/us-0069-character-sheet-inspector-and-active-session-binding.md)
- [`prd-0023-unified-frontend-application-shell-and-campaign-hub.md`](../../product/accepted/prd-0023-unified-frontend-application-shell-and-campaign-hub.md)

## Detailed Specification & Implementation Plan
1. Remove the fixed `campaignId`, `sessionId`, `campaignTitle`, `sessionTitle`, and `user-valeros` defaults. Read the campaign id from `#/campaigns/:campaignId`, and the session id from `#/campaigns/:campaignId/sessions/:sessionId` or `/lobby/:sessionId`.
2. Remove the campaign title resolver that maps ids `'4'` and `'5'`. The title comes from `fetchCampaign(campaignId)`.
3. Feed `runefoble-campaign-nav` from `fetchCampaigns()` in the header. Remove the component's default list.
4. Replace `resolveActiveCharacter()`'s placeholder with `null`. The character view shows an empty state with a "Create character" action.
5. Remove the invented stats in `handleSelectCharacter()`. Load the character detail through `fetchCharacterDetail`. If it fails, show the error state from TASK-0640.
6. Remove guardrail, spell slot, and priority defaults from the character sheet branch. Load them from the character record. A new character has empty values.
7. Remove the profile fallback in `runefoble-user-profile.ts`. Show the profile from `GET /api/v1/profile`, or the error state.
8. Remove the `/assets/portraits/fighter.svg` reference. The avatar uses the character's own portrait or a neutral placeholder element with no asset path.

## Frontdoor Blackbox Test Plan
Playwright BDD (`e2e/features/app_shell_routing_state.feature`), using only public UI and routes:
- Scenario: Opening campaign B shows campaign B's title, not "Tomb of the Star-Eater".
  - Given the DM created campaigns "Harbour Watch" and "Glass Crypt" through the dashboard
  - When the DM opens "Glass Crypt"
  - Then the header shows "Glass Crypt" and the campaign switcher lists both campaigns from the API.
- Scenario: A user without characters sees an empty roster, not a placeholder.
  - Then the character view shows the empty state and no element named "Adventurer" exists.
- Before the fix these scenarios FAIL. After the fix they PASS.

Unit tests in `frontend/test/route-state.test.ts` cover the route parser.

## Definition of Done
1. `grep -rn "Tomb of the Star-Eater\|session-tomb-14\|char-placeholder\|user-valeros\|fighter.svg" frontend/src` returns no production match. Verified by a test.
2. The campaign switcher renders campaigns from the API, and the default list is removed from `runefoble-campaign-nav.ts`.
3. The Playwright BDD scenarios pass in all three browsers.
4. `pnpm run lint`, `pnpm test`, and `pnpm run build` pass.
5. Storybook stories for the nav and profile components still build with explicit story props.
6. Each changed file is under 500 lines.
