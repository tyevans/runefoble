---
id: '0649'
title: E2E Steps Remove Injected Component State, Synthetic Events, and Direct DOM Theme Writes
status: Refined
created: 2026-11-17
dependencies:
- TASK-0512
- TASK-0447
governing_adrs:
- ADR-0014
governing_prds:
- PRD-0023
governing_stories:
- US-0016
- US-0063
- US-0065
target_release: 0.9.0
severity: high
source_audits:
- w2-e2e-bdd.md
---

# TASK-0649: E2E Steps Remove Injected Component State, Synthetic Events, and Direct DOM Theme Writes

## Status
Refined

Audit 2026-11-17: blocked by proposed TASK-0512 and TASK-0447. The step files must be decomposed first.

## Summary
Several Playwright BDD steps change the application from the inside: they write private component fields, dispatch synthetic DOM events, set the URL hash to skip a flow, and write `data-theme` and `localStorage` directly. Each one breaks ADR-0014 and Hard Invariant 7. Remove every such backdoor. Each step must act through a visible control or a public route, and it must fail when that control is missing. Campaign hub setup (TASK-0512) and the character sheet steps (TASK-0447) are split first, so the files stay under 500 lines during this work.

## Problem Statement
- `e2e/steps/campaign_hub_steps.ts:168-170` swallows role-assignment errors with `catch { // In-memory fallback }`.
- Lines 176-214 write `app.campaignMembers` on the `runefoble-app` element (private state). They push synthetic members, including `character_name: 'Thorin Stonehelm'`. The assertion then checks the roster the test itself wrote.
- `e2e/steps/vtt_steps.ts:233-252` dispatches a synthetic `move-token` `CustomEvent` into `runefoble-app` `shadowRoot` > `runefoble-board` after the real drag. The step does not check that the drag succeeded. The chronicle assertion can pass because of the synthetic event.
- `e2e/steps/vtt_steps.ts:189-196` sets `window.location.hash` directly when the Launch button is missing. The scenario skips the launch flow it names.
- `e2e/steps/common_steps.ts:64-75` (fallback 3): when no theme control is visible, the step sets `data-theme`, writes `localStorage`, and dispatches `theme-changed`. The assertion at lines 107-113 reads the same attribute, so the step can pass with no user action.

## Documentation & Architecture Review
- `docs/how-to/test-user-flows-with-playwright-bdd.md` line 110 already says not to spy on private component methods. The steps violate that rule. Update the how-to with the rule and one correct example.
- ADR-0014: setup and assertions use only public frontdoors (UI forms, public REST routes, emitted events).
- Hard Invariant 7 forbids backdoor state manipulation.

## Product & User Story References
- [`us-0063-campaign-creation-dashboard-and-zanzibar-roles.md`](../../user_stories/accepted/us-0063-campaign-creation-dashboard-and-zanzibar-roles.md)
- [`us-0065-game-session-lobby-readiness-and-launch.md`](../../user_stories/accepted/us-0065-game-session-lobby-readiness-and-launch.md)
- [`us-0016-themable-frontend-with-bauhaus-default.md`](../../user_stories/accepted/us-0016-themable-frontend-with-bauhaus-default.md)

## Detailed Specification & Implementation Plan
1. `campaign_hub` steps: remove the `catch` at lines 168-170. Role setup calls `POST /api/v1/campaigns/:id/roles` through `e2e/support/frontdoor_api.ts` and throws on failure. Remove lines 176-214. Assert the roster from the visible members list and from `GET /api/v1/campaigns/:id/members`.
2. `vtt_steps`: remove the `move-token` dispatch at lines 233-252. The drag is the only action. Assert that the board token moved to the expected cell (for example, Evelyn's token at (3,3)) using the visible cell label, and that the chronicle feed item appears through the UI. Remove the hash fallback at lines 189-196. If Launch is not visible, the step fails.
3. `common_steps`: delete fallback 3 (lines 64-75). The step clicks the real theme control (settings modal or switcher, decided with TASK-0376 and TASK-0380). If the control is not visible, the step fails. The assertion reads the theme from the user-visible label or the control state.
4. Search all of `e2e/steps` and `e2e/support` for `app.`, `shadowRoot`, `dispatchEvent`, `localStorage`, `window.location`, and `data-theme` writes. Each hit is removed or justified in a comment that cites ADR-0014. Justified hits must be reads only.
5. Keep every file under 500 lines.
6. `docs/how-to/test-user-flows-with-playwright-bdd.md` (w2-e2e-bdd F11): replace the example step files `e2e/steps/auth_steps.ts` and `e2e/steps/campaign_steps.ts` with the real files, replace the unimplemented example steps with steps that exist, and list all personas the code accepts (`evelyn`, `valeros`, `sarah`, and the `gm` alias from `e2e/support/auth_fixtures.ts:138-156`).

## Frontdoor Blackbox Test Plan
These scenarios already exist. The change removes their backdoors, so they must still pass through the UI:
- `campaign_hub.feature`: "DM sees the roster after assigning a role" passes with the role set through the public route.
- `session_lobby_and_vtt.feature`: "DM moves a token by dragging" asserts the moved cell and the chronicle item through the UI.
- `smoke.feature`: "Player switches design system theme to Dark Fantasy" fails when the theme control is removed from the test build, and passes when the control is clicked.
- Add a negative scenario to prove the guard: with the Launch control hidden by a test that removes nothing (use the real state where the DM is a player), the step fails with a clear message.
- Confirm by `grep` that no step file contains a backdoor pattern from item 4.

## Definition of Done
1. The grep in item 4 returns no backdoor write in `e2e/steps` or `e2e/support`.
2. Every affected scenario passes in chromium, firefox, and webkit with `make test-e2e`.
3. The theme step fails when no theme control is visible (verified by a temporary local run, not committed).
4. `docs/how-to/test-user-flows-with-playwright-bdd.md` shows a correct example and no private-method spy.
5. Each step file is under 500 lines.
6. The how-to examples name real step files and the full persona list (item 6 of the plan).
7. Changelog entry is not required (test-only change).

## Orchestrator Addenda (2026-11-17)

Source: `.audit/synth/discovered-round1.md`.

- `e2e/features/asset_forge.feature:17` and `e2e/steps/asset_forge_steps.ts:6` inject a 503 at the network boundary. Decide under ADR-0014 whether this is an allowed fault double. If not, stop the service instead.
