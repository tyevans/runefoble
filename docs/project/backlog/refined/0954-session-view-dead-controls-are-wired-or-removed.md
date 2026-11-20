---
id: '0954'
title: Session View Controls Work or Are Removed
status: Refined
created: 2026-11-19
dependencies:
- '0952'
governing_adrs:
- ADR-0013
- ADR-0014
- ADR-0015
governing_prds:
- prd-0025-voice-first-release-one
governing_stories:
- us-0002-absent-player-mimicked-by-ai-with-penalties
target_bc: frontend
target_release: 1.0.0
---

# TASK-0954: Session View Controls Work or Are Removed

## Status

Refined. Release One (PRD-0025). Items 8 and 10 of section 4 in `.audit/research/r1-core-journeys.md`.

This record depends on TASK-0952. The stance drawer needs the real stand-in state, and that state comes from the lobby stand-in routes. The research report does not list this dependency.

## Summary

Three groups of controls on the live session view do not work as shown. The stance drawer always shows "Stand-In Active". It does not save the chosen stance. It appears for every player with a bound character. Two DM board controls, the hidden-layer toggle and the trap preset event, dispatch events that no code receives.

This task makes each control either work through a public route or removes it. The controls are in the session view and its DM board area only. The audio recap button on the analytics tab is outside this task.

## Problem Statement

Evidence from `.audit/research/r1-core-journeys.md`, section 4, items 8 and 10, checked against the code.

- `frontend/src/app/absentee-overlays.ts:15`: the drawer passes `.standInActive=${true}` every time.
- `services/the_watcher/ui/src/runefoble-absentee-directive.ts:22`: the default `characterName` is `'Sarah'`.
- `services/the_watcher/ui/src/runefoble-absentee-directive.ts:24-25`: the defaults are `standInActive = true` and `currentStance = 'defensive'`.
- `services/the_watcher/ui/src/runefoble-absentee-directive.ts:14-18`: the stance ids are `defensive`, `cautious` and `heroic`.
- `services/the_watcher/ui/src/runefoble-absentee-directive.ts:46-53`: `selectStance` sets local state and dispatches `directive-changed` and `stance-selected`. The App Shell shows a toast (`absentee-overlays.ts:15`). Nothing is saved.
- `frontend/src/views/session-view.ts:52-53`: the "Stance Directives" button shows for any bound character, even when no stand-in is active.
- `libs/runefoble_platform/src/runefoble_platform/stand_in_guardrails.py:31-34`: `StandInGuardrailPolicy` has no stance field, and `extra="forbid"` rejects unknown keys.
- `gateway/api/src/gateway_api/routers/characters_spells_guardrails_proxy.py:72-76`: the gateway proxies `PUT /api/v1/characters/{id}/guardrails`. This is the save path.
- `services/board_state/ui/src/runefoble-dm-trap-controls.ts:50`: `trap-selected` is dispatched. No listener exists.
- `services/board_state/ui/src/runefoble-dm-trap-controls.ts:55`: `layer-toggled` is dispatched. No listener exists. The layer has no effect on the board.
- `services/board_state/ui/src/runefoble-dm-trap-controls.ts:102-103`: the "Visible" or "Hidden" button toggles `layerVisible` only.
- `frontend/src/views/session-view.ts:16-20`: the DM trap controls render inside the board area for a DM.

## Documentation & Architecture Review

- `docs/how-to/configure-stand-in-guardrails-and-hot-swap.md`: the guardrail policy and stance. Update it with the stance field.
- `docs/how-to/manage-secret-dm-traps-and-map-triggers.md`: the DM trap controls. Update the control list.
- `docs/reference/microfrontend-architecture.md`: the element catalog. Keep it consistent.
- ADR-0015: no default name, no default stance, and no fake layer state.
- ADR-0013: the directive and trap controls are owned by `services/the_watcher/ui/` and `services/board_state/ui/`. The session view composes them.

## Product & User Story References

- PRD-0025, "What good looks like", step 2 (stand-ins survive a reload) and the principle "The Watcher is an assistant, never a dictator".
- US-0002: the absent player mimicked by the AI, with the stance guardrails.

## Detailed Specification & Implementation Plan

1. **Drawer state.** The App Shell passes the bound character's real `isAiStandIn` (`frontend/src/views/session-view.ts`). Remove the fixed `.standInActive=${true}` at `absentee-overlays.ts:15`.
2. **Drawer button.** Show "Stance Directives" only when the bound character is an active stand-in.
3. **Remove substitute defaults.** In `runefoble-absentee-directive.ts`, remove the defaults `'Sarah'` (line 22) and `'defensive'` (line 25). The App Shell passes the name. An unset stance shows "No stance set".
4. **Save the stance.** Add `stance: Literal["defensive", "cautious", "heroic"] | None = None` to `StandInGuardrailPolicy`. The drawer saves through `PUT /api/v1/characters/{id}/guardrails`. The PUT body is the full policy, so the App Shell first reads `GET /api/v1/characters/{id}/guardrails`, changes the stance, and sends the result. The App Shell shows a toast on success and the server message on failure.
5. **Trap controls.** Remove the "Visible" or "Hidden" button and the `layer-toggled` dispatch. The board has no layer state to change. Remove the `trap-selected` dispatch, because the preset fields are set inside the element.
6. **Other DM board controls.** The implementer checks each remaining control in `renderBoardDmControls` (`frontend/src/views/session-view.ts:16-20`). A control that does not reach a public route is removed. "Switch Map" is listed here because the research report does not verify it.
7. **Storybook.** Update the directive and trap control stories for the new props. The stories show zero console errors.
8. **Docs.** Update the two how-to pages named above.
9. **Chronicle audio recap button.** `services/campaign_analytics/ui/src/runefoble-chronicle-timeline.ts:96` has an audio recap control with no working route. Remove it, or wire it if a public route exists. Record the choice.

## Frontdoor Blackbox Test Plan

Playwright BDD scenarios in `e2e/features/session_view_controls.feature`. Setup uses only the UI. Each scenario runs in chromium, firefox and webkit.

```gherkin
@US-0002
Feature: Session view controls work or are removed

  Scenario: A stand-in sees the real stand-in state and keeps the chosen stance
    Given Sarah marks herself absent in the lobby "Stance Lobby" in the UI
    And Evelyn runs the lobby "Stance Lobby" in the UI
    When Sarah opens "Stance Directives" from her session view
    Then the status of the stance drawer reads "Stand-In Active"
    When Sarah selects the stance "Cautious"
    And Sarah reloads the session view
    And Sarah opens "Stance Directives"
    Then the selected stance is "Cautious"

  Scenario: A present player has no stance drawer
    Given Valeros is on the active session "Stance Lobby" with his character present
    Then no "Stance Directives" button is shown to Valeros

  Scenario: The DM board shows no hidden-layer toggle
    Given Evelyn is on the active session "Stance Lobby" with a battlemap in the UI
    Then no "Hidden" layer toggle is shown
    And the "Arm Cell" control is shown
```

## Definition of Done

1. The drawer status comes from `isAiStandIn`. Scenario 1 passes in chromium, firefox and webkit.
2. `StandInGuardrailPolicy` has the `stance` field. A test in `libs/runefoble_platform` covers the accepted values and the default `None`.
3. The guardrail PUT with a stance is tested through a live loopback character_sheet upstream.
4. `git grep -n "'Sarah'\|'defensive'" services/the_watcher/ui/src/runefoble-absentee-directive.ts` returns no match.
5. `git grep -n "layer-toggled\|trap-selected" services/board_state/ui/src` returns no match.
6. Each DM board control has a route or is removed. The record in the pull request lists the check for each control.
7. The directive and trap control stories show zero console errors.
8. The two how-to pages match the code.
9. CHANGELOG `[Unreleased]` records the stance save under `Added` and the removed controls under `Fixed`.
10. No changed source file is over 500 lines.

## Audit Provenance

- Severity: medium (dead controls mislead the DM and the stand-in)
- Source audits: `.audit/research/r1-core-journeys.md` (section 4, items 8 and 10)
