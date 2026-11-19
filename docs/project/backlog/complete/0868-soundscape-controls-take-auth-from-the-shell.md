---
id: '0868'
title: Soundscape Controls Send Ducking With the Shell Bearer Token
status: Complete
created: 2026-11-18
dependencies: []
governing_adrs:
- ADR-0004
- ADR-0013
- ADR-0015
governing_prds:
- PRD-0010
governing_stories:
- US-0039
target_bc: soundscape
target_release: 0.9.0
---
# TASK-0868: Soundscape Controls Send Ducking With the Shell Bearer Token

## Status
Complete

## Summary
The soundscape HUD widget takes a raw `authorization` string. No caller sets it. A duck request therefore carries no `Authorization` header. Ducking is then not applied. The widget must get its auth headers from the same consumer that other service UI packages use.

## Problem Statement
- `services/soundscape/ui/src/runefoble-soundscape-controls.ts:13`: `@property authorization = ''`.
- `runefoble-soundscape-controls.ts:96`: the value is passed to `postDuck`. `services/soundscape/ui/src/soundscape-duck-api.ts:16-34` builds the header from it.
- No file in `frontend/src` or `services/*/ui/src` sets `authorization=` (stories excluded). The widget is mounted by `frontend/src/components/plugins/plugin_registry.ts:98` with no attribute. Result: the duck request sends no token. The panel then shows "Ducking was not applied". Confirm the gateway rejects this request before merge. The report expects a 401.
- About nineteen service UI modules use `AuthConsumerController`. `services/rules_compendium/ui/src/runefoble-rules-lookup.ts` is one example. The soundscape widget is the outlier.

## Documentation & Architecture Review
- ADR-0013 (service UI packages are self-contained and use the shared auth helper).
- ADR-0015 (no hidden failure).
- `docs/how-to/manage-dynamic-soundscapes-and-audio-ducking.md` describes the duck call. Update it if it names the `authorization` property.

## Product & User Story References
- PRD-0010 (adaptive soundscape). US-0039 (encounter tension and foley).

## Detailed Specification & Implementation Plan
1. In `runefoble-soundscape-controls.ts`, add `private readonly auth = new AuthConsumerController(this)` from `@runefoble/ui-core`, as `runefoble-rules-lookup.ts` does. Remove the `authorization` property.
2. Change `postDuck` in `soundscape-duck-api.ts` to take `authHeaders: () => Promise<Record<string, string>>`. It awaits the headers before the request.
3. Update the story in `runefoble-soundscape-controls.stories.ts:105`. Use a stub auth consumer in place of the attribute.
4. Keep the existing failure message. It must not report success when the request fails.

## Frontdoor Blackbox Test Plan
- Playwright BDD (ADR-0014). A signed-in DM with the App Shell opens the soundscape widget and engages a duck. Assert that the request reaching the gateway has `Authorization: Bearer`, and that the widget shows no error.
- Negative scenario: the gateway returns 401 for the duck request. The widget shows "Ducking was not applied" with the server detail.
- Storybook: the story renders with a stub consumer and shows zero console errors.

## Definition of Done
- No `authorization` property in the soundscape service UI.
- Playwright BDD scenarios pass without backdoor state changes.
- Storybook story has zero console errors.
- `pnpm run build` and `make lint` pass. No file over 500 lines.
- No backward-compatibility shim (DoR 9).

## Audit Provenance
- Severity: high
- Source audits: `frontend-ui`

## Completion Note
Unit tests, typecheck and the gateway duck test pass. Playwright and Storybook checks were not run in the worker; the orchestrator gate builds the frontend.
