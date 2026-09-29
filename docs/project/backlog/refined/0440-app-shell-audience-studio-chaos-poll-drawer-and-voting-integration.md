---
id: '0440'
title: App Shell Audience Studio Chaos Poll Drawer & Live Voting Integration
status: Refined
created: 2026-09-29
dependencies:
- TASK-0051
- TASK-0358
- TASK-0439
governing_adrs:
- ADR-0004
- ADR-0006
- ADR-0010
- ADR-0013
governing_prds:
- PRD-0011
- PRD-0023
governing_stories:
- US-0006
- US-0030
- US-0031
- US-0065
target_release: 0.9.0
---

# TASK-0440: App Shell Audience Studio Chaos Poll Drawer & Live Voting Integration

## Status
Refined

## Summary
Mount and integrate the `<runefoble-audience-studio>` microfrontend within the App Shell (`frontend/src/runefoble-app.ts`) as a slide-out DM chaos moderation drawer and floating stream spectator widget. Wire bidirectional WebSocket events for live poll progress, vote broadcasts, and DM proposal approval/veto actions directly through the Gateway API.

## Problem Statement
The Audience Studio Web Component (`<runefoble-audience-studio>`) exists in `services/audience_studio/ui/` and is exported in `frontend/src/components/audience-studio.ts`. However, it is never instantiated or mounted in the main App Shell. DMs cannot open a moderation panel to review incoming audience chaos poll results, and viewers watching through the web client cannot view active poll timers or cast votes within the session.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/how-to/orchestrate-audience-chaos-polls.md`: Managing live audience chaos polls, spectator votes, and DM approval queues.
  - `docs/how-to/mount-community-plugin-ui-extension-slots.md`: Mounting Lit Web Components into designated extension slots.
  - `docs/reference/design-tokens-and-themes.md`: Bauhaus token inheritance and responsive slide-out drawer conventions.
- **Governing Architecture & ADRs**:
  - **ADR-0004: Lit Web Components and Storybook UI**: Microfrontend encapsulation and DOM CustomEvent dispatching.
  - **ADR-0006: Redis Streams Distributed Domain Event Streaming**: Real-time poll updates streamed via WebSockets.
  - **ADR-0013: Frontend Microfrontend Architecture**: Service bounded context components composed into App Shell.

## Product & User Story References
- [`prd-0011-live-spectator-studio-and-audience-interactivity.md`](../../product/accepted/prd-0011-live-spectator-studio-and-audience-interactivity.md)
- [`prd-0023-unified-frontend-application-shell-and-campaign-hub.md`](../../product/accepted/prd-0023-unified-frontend-application-shell-and-campaign-hub.md)
- [`us-0030-obs-transparent-party-vitals-and-multi-track-audio.md`](../../user_stories/accepted/us-0030-obs-transparent-party-vitals-and-multi-track-audio.md)
- [`us-0031-live-stream-audience-chaos-polls-and-rumors.md`](../../user_stories/accepted/us-0031-live-stream-audience-chaos-polls-and-rumors.md)
- [`us-0065-game-session-staging-lobby-and-pre-game-assembly.md`](../../user_stories/accepted/us-0065-game-session-staging-lobby-and-pre-game-assembly.md)

## Detailed Specification & Implementation Plan
1. **App Shell Integration (`frontend/src/runefoble-app.ts`)**:
   - Add state property `isAudienceDrawerOpen: boolean` and toggle button in DM toolbar.
   - Conditionally render `<runefoble-audience-studio>` in a slide-out drawer or overlay when viewing live sessions or spectator streams.
   - Bind campaign ID, session ID, and role permissions (`canApproveChaos`) to component properties.
2. **WebSocket Event Dispatching**:
   - Listen to custom events from `<runefoble-audience-studio>`:
     - `@audience-poll-created`: Send creation payload over `/ws/audience/{campaign_id}`.
     - `@audience-vote-cast`: Send vote payload.
     - `@audience-proposal-approved`: Send approval action.
     - `@audience-proposal-vetoed`: Send veto action.
   - Receive incoming WebSocket broadcast messages (`poll_started`, `poll_tally_updated`, `proposal_queued`, `proposal_resolved`) and pass them to the component.
3. **Frontend Integration Tests (`frontend/test/audience-studio-integration.test.ts`)**:
   - Verify drawer toggle, property binding, custom event dispatches, and incoming WebSocket state synchronization.

## INVEST Criteria Evaluation
- **Independent (I)**: Integrates UI microfrontend into App Shell independently of backend worker internals.
- **Negotiable (N)**: Drawer position (left, right, or overlay) and animation timing can be adjusted.
- **Valuable (V)**: Empowers DMs to run live interactive polls and engage spectators directly.
- **Estimable (E)**: Follows existing drawer patterns in App Shell (e.g. settings modal, dice roller).
- **Small (S)**: Scope bounded to App Shell component wiring (< 120 lines) and one integration test file.
- **Testable (T)**: Frontdoor Lit component testing asserting DOM rendering and dispatched CustomEvents.

## Definition of Done
1. `<runefoble-audience-studio>` successfully mounted and toggleable in App Shell.
2. Real-time poll events propagate between App Shell and Audience Studio component.
3. Frontdoor blackbox test suite `frontend/test/audience-studio-integration.test.ts` passes with 100% assertions.
4. Code passes `npm run lint` and TypeScript compilation (`npm run check`).
