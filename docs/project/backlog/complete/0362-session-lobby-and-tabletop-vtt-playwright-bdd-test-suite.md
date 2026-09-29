---
id: '0362'
title: Session Lobby & Tabletop VTT Playwright BDD Test Suite
status: Complete
created: 2026-09-28
dependencies:
- TASK-0354
- TASK-0358
- TASK-0359
governing_adrs:
- ADR-0004
- ADR-0005
- ADR-0010
- ADR-0013
- ADR-0014
governing_prds:
- PRD-0002
- PRD-0005
- PRD-0023
governing_stories:
- US-0002
- US-0005
- US-0065
target_release: 0.9.0
pr_url: https://github.com/tyevans/runefoble/pull/359
---
# TASK-0362: Session Lobby & Tabletop VTT Playwright BDD Test Suite

## Status
Refined

## Summary
Implement a multi-browser Playwright BDD test suite (`e2e/features/session_lobby_and_vtt.feature`) verifying the pre-game staging lobby, readiness toggling, absentee stand-in flags, live session launching, and real-time tabletop VTT token synchronization per ADR-0014. Automate end-to-end verification across two concurrent browser sessions (Dungeon Master and Player) connected over real WebSockets.

## Problem Statement
The transition from pre-game session lobby into live tactical gameplay is the most dynamic user flow in Runefoble. Previously, the lobby readiness checkboxes and absentee stand-in toggles operated in isolated local DOM states, and board token movements were verified only via unit tests without verifying multi-client WebSocket broadcasts in real browser viewports. 

To ensure synchronous, low-friction session starts and responsive tactical board actions, we must establish automated Playwright BDD tests executing multi-user scenarios across real browser contexts without backdoor state manipulation.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/how-to/coordinate-game-session-lobby-and-readiness.md`: Pre-game assembly, player presence, readiness, and absentee stand-ins.
  - `docs/how-to/interact-with-tactile-board-and-ghost-previews.md`: Tactile token kinematics, 5-ft distance measuring, and radial menus.
  - `docs/how-to/orchestrate-app-shell-views-and-session-transitions.md`: View staging transitions from lobby to live VTT.
- **Governing Architecture & ADRs**:
  - **ADR-0004: Lit Web Components and Storybook UI**: Web component presentation.
  - **ADR-0005: WebSocket Real-Time Synchronization Architecture**: WebSocket event protocol.
  - **ADR-0010: Real-time Audio and Tactical Board Synchronization**: Real-time board sync.
  - **ADR-0014: Behavior-Driven Development (BDD) with Gherkin User Stories and Playwright End-to-End Validation**: BDD testing framework.

## Scope of Work & Implementation Plan
1. **Gherkin Feature Specification (`e2e/features/session_lobby_and_vtt.feature`)**:
   - **Scenario 1: Multi-User Lobby Assembly and Readiness**:
     - `Given Evelyn is hosting session "Lobby 15" for campaign "4"`
     - `And Valeros joins "Lobby 15" in a separate browser`
     - `When Valeros checks "Ready to Play"`
     - `Then Evelyn's lobby view updates in real time showing Valeros as "Ready"`.
   - **Scenario 2: Marking Absentee AI Stand-In**:
     - `When Sarah opens "Lobby 15" and checks "Mark Absent (AI Stand-In)"`
     - `Then the participant card displays the "AI Stand-In" badge across all connected screens`.
   - **Scenario 3: DM Launching Active Tabletop VTT**:
     - `When Evelyn clicks "Launch Session"`
     - `Then both Evelyn and Valeros's browsers navigate automatically to "#/campaigns/4/sessions/15"`
     - `And the tactical board `<runefoble-board>` renders with dynamic grid bounds`.
   - **Scenario 4: Live Token Kinematics and Movement Sync**:
     - `When Valeros drags his token from coordinate (2, 2) to (3, 3)`
     - `Then the token coordinate on Evelyn's screen smoothly moves to (3, 3)`
     - `And the chronicle feed logs the move action`.
2. **Step Definitions Implementation (`e2e/steps/vtt_steps.ts`)**:
   - Utilize Playwright's multi-context API (`browser.newContext()`) to simulate concurrent DM and Player browser windows.
   - Use shadow-piercing locators to interact with `<runefoble-session-lobby>` and canvas/pointer drag events on `<runefoble-board>`.
   - Verify WebSocket messages are exchanged through the API Gateway WebSocket stream without dropped frames.
3. **Execution & CI Integration**:
   - Verify headless multi-context execution runs reliably in under 30 seconds.

## INVEST Criteria Evaluation
- **Independent (I)**: Self-contained within session staging and live VTT game loops.
- **Negotiable (N)**: Specific coordinate paths and character names can vary.
- **Valuable (V)**: Validates Runefoble's core real-time collaborative promise ("Speak and the board obeys") in actual browser engines.
- **Estimable (E)**: Built on existing WebSocket protocols and Lit component contracts.
- **Small (S)**: Feature file and TypeScript step definitions (< 250 lines).
- **Testable (T)**: Directly testable via Playwright dual-context browser automation.

## Definition of Done
1. `e2e/features/session_lobby_and_vtt.feature` passes across Chromium and Firefox.
2. Concurrent DM and Player browser contexts verify live WebSocket synchronization without page refresh.
3. All token movements, readiness toggles, and session launch transitions are verified through frontdoor UI actions.
4. All source files conform to the <500 line limit (Hard Invariant 6).
