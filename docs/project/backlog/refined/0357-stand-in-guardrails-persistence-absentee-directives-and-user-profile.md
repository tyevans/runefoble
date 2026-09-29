---
id: '0357'
title: Stand-In Guardrails Persistence, Absentee Directives & User Profile Management
status: Refined
created: 2026-09-28
dependencies:
- TASK-0003
- TASK-0011
- TASK-0073
- TASK-0248
governing_adrs:
- ADR-0003
- ADR-0004
- ADR-0008
- ADR-0013
governing_prds:
- PRD-0003
- PRD-0023
governing_stories:
- US-0004
- US-0066
target_release: 0.9.0
---

# TASK-0357: Stand-In Guardrails Persistence, Absentee Directives & User Profile Management

## Status
Refined

## Summary
Eradicate unpersisted guardrail stubs and read-only profile limitations by ensuring `<runefoble-stand-in-guardrails>` always renders on the character sheet with sensible defaults, wiring `@guardrails-saved` and `@hot-swap-requested` to backend endpoints, mounting `<runefoble-absentee-directive>` and `<runefoble-absentee-recap>` into the live session and re-entry flow, and implementing an editable profile mode with backend persistence on `gateway-api`.

## Problem Statement
Stand-in guardrails and absentee features are critical to Runefoble's core value proposition ("A missing player never cancels game night"). However, the implementation is currently fragmented:
1. In `frontend/src/runefoble-app.ts:225`, `<runefoble-stand-in-guardrails>` is conditionally rendered only if `char?.stand_in_guardrails` is present. Because `gateway-api` character responses omit `stand_in_guardrails`, the component is never rendered when connected to the backend.
2. In `runefoble-stand-in-guardrails.ts:57-78`, saving guardrails shows a local 3-second toast message but never issues an HTTP request (`PUT /api/v1/characters/{id}/guardrails`). In addition, `runefoble-app.ts` does not attach listeners for `@guardrails-saved` or `@hot-swap-requested`.
3. The components `runefoble-absentee-directive` (mobile stance carousel and voting) and `runefoble-absentee-recap` (audio chronicle and absence penalty badges) exist in microfrontends but are never mounted anywhere in the application.
4. The User Profile view (`frontend/src/components/runefoble-user-profile.ts`) displays static user claims with no edit controls, `appDataService` lacks `updateProfile()`, and `gateway-api` has no profile update endpoint.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/how-to/configure-stand-in-guardrails-and-hot-swap.md`: Tactical guardrails, 0-HP stabilization, and mid-session hot-swap takeover.
  - `docs/how-to/coordinate-game-session-lobby-and-readiness.md`: Toggling readiness and absentee AI stand-ins.
- **Governing Architecture & ADRs**:
  - **ADR-0003: AI Stand-in Tactical Guardrails and Stance Directives**: Autonomous DM surrogate behavior.
  - **ADR-0004: Lit Web Components and Storybook UI**: Component encapsulation and event dispatch.
  - **ADR-0008: Audio Chronicle and Session Recap**: Absentee recap audio playback.
  - **ADR-0013: Frontend Microfrontend Architecture**: Microfrontend composition in App Shell.

## Scope of Work & Implementation Plan
1. **Unconditional Guardrails Rendering & Defaults (`frontend/src/runefoble-app.ts`)**:
   - Update `renderActiveView('character-sheet')` to always mount `<runefoble-stand-in-guardrails>`, providing default values (e.g. `riskThreshold: 'cautious'`, `avoidMelee: true`, `permadeathSafeguard: true`) when `char?.stand_in_guardrails` is undefined.
2. **Backend Guardrails Endpoint & Gateway Routing**:
   - Expose `PUT /api/v1/characters/{id}/guardrails` on `gateway-api` and route to `character_sheet:8003`.
   - Update `appDataService.ts` with `updateCharacterGuardrails(characterId, payload)`.
   - Bind `@guardrails-saved` in `runefoble-app.ts` to persist changes and display a confirmed toast notification.
   - Bind `@hot-swap-requested` in `runefoble-app.ts` to call `POST /api/v1/sessions/{sessionId}/hot-swap`.
3. **Mount Absentee Directives & Recap in Active Sessions**:
   - In `runefoble-app.ts` (`session-active` or `session-lobby`), if a player marks their character as absent or is marked absent by the DM, render `<runefoble-absentee-directive>` in a dedicated drawer or modal.
   - When a returning player rejoins a session after an absence, trigger `<runefoble-absentee-recap>` displaying health deltas, rewards, and playful miss penalties (`drunk`, `foolishness`).
4. **Editable User Profile (`frontend/src/components/runefoble-user-profile.ts`)**:
   - Add an "Edit Profile" toggle with inputs for Display Name, Avatar URL, and Bio.
   - Add `updateProfile(payload: UpdateProfilePayload)` in `appDataService.ts`.
   - Add `PATCH /api/v1/profile` on `gateway/api/src/gateway_api/routers/auth.py`.
5. **Blackbox TDD Tests**:
   - Author `tests/test_blackbox_standin_guardrails_persistence.py` testing guardrail updates and hot-swap requests through the gateway.
   - Update `frontend/test/character-management-and-profile.test.ts` to assert profile editing and guardrail event handling.

## INVEST Criteria Evaluation
- **Independent (I)**: Self-contained within stand-in guardrail configurations and user profile views.
- **Negotiable (N)**: Default guardrail thresholds and profile field options can be tuned.
- **Valuable (V)**: Restores critical AI stand-in safety features, ensuring players can confidently entrust characters to The Watcher.
- **Estimable (E)**: Guardrail data structures and schemas are established in `services/character_sheet`.
- **Small (S)**: Confined to App Shell event binding, profile template, and gateway router (< 150 lines per file).
- **Testable (T)**: Tested with frontdoor API requests and Lit component event assertions.

## Definition of Done
1. Stand-in guardrails panel renders consistently on every character sheet.
2. Saving guardrails updates backend persistence and reflects changes on subsequent views.
3. Mid-session hot-swap button issues a valid session hot-swap request.
4. User profile supports editing display name and avatar with backend persistence.
5. Blackbox test suite passes with 100% assertions.
