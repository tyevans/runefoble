---
id: 0358
title: Live Tabletop VTT WebSocket Event Mesh, Plugin Slots & Tangential Controls
  Integration
status: Complete
created: 2026-09-28
dependencies:
- TASK-0004
- TASK-0010
- TASK-0014
- TASK-0022
- TASK-0249
governing_adrs:
- ADR-0004
- ADR-0005
- ADR-0010
- ADR-0013
governing_prds:
- PRD-0002
- PRD-0005
- PRD-0023
governing_stories:
- US-0002
- US-0005
- US-0065
target_release: 0.9.0
pr_url: https://github.com/tyevans/runefoble/pull/351
---
# TASK-0358: Live Tabletop VTT WebSocket Event Mesh, Plugin Slots & Tangential Controls Integration

## Status
Refined

## Summary
Transform the active VTT view from a partially stubbed layout into a complete live tabletop system by wiring missing session lobby events (`@toggle-readiness`, `@toggle-stand-in`), passing `websocketUrl` to `<runefoble-board>`, expanding `runefoble-app.ts` WebSocket message processing to handle dice rolls, turn changes, AoE spells, and VFX, registering core microfrontends into default plugin slots (`hud-widget`, `dice-panel`, `sidebar-tool`), and removing hardcoded grid/atmosphere constants.

## Problem Statement
The active VTT and session views currently suffer from significant integration gaps and mock shortcuts:
1. In `frontend/src/runefoble-app.ts:228`, `<runefoble-session-lobby>` dispatches `@toggle-readiness` and `@toggle-stand-in`, but the App Shell attaches no listeners. Checking "Ready to Play" or marking a character absent does not save state or notify connected party members.
2. In `session-active` (lines 232–236), `<runefoble-board>` has static `.cols=${8} .rows=${8}` hardcoded, ignoring dynamic map bounds. The App Shell only listens for `@move-token`, dropping all radial menu actions (`@token-action`), AoE spell templates (`@aoe-place`), ghost confirmations (`@confirm-ghost`), and spell VFX.
3. `<runefoble-board>` is not passed `websocketUrl`, leaving its internal WebSocket connection null and causing radial menu socket transmissions to fail silently.
4. Plugin slots (`hud-widget`, `dice-panel`, `sidebar-tool`) render blank in production because `pluginRegistry` is never seeded with default components. Over 10 completed microfrontends (such as `runefoble-initiative-tracker`, `runefoble-dice-roller`, `runefoble-dice-tray-3d`, `runefoble-soundscape-controls`, `runefoble-dm-whisper-bar`, `runefoble-dm-trap-controls`) exist only in Storybook stories.
5. In `runefoble-app.ts:130-137`, the WebSocket client only processes `session_started`, `board_move`, and `speech_action`, dropping all other event types (dice rolls, turn advancements, HP deltas, AoE markers).

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/how-to/mount-community-plugin-ui-extension-slots.md`: Mounting Lit Web Components into designated extension slots with Shadow DOM event isolation.
  - `docs/how-to/interact-with-tactile-board-and-ghost-previews.md`: Tactile token kinematics, ghost previews, and AoE spell templates.
  - `docs/how-to/broadcast-obs-stream-overlay-and-cinematic-camera.md`: Real-time WebSocket stream overlays and director tracking.
- **Governing Architecture & ADRs**:
  - **ADR-0004: Lit Web Components and Storybook UI**: Web component presentation in Storybook and App Shell.
  - **ADR-0005: WebSocket Real-Time Synchronization Architecture**: WebSocket event routing and state synchronization.
  - **ADR-0010: Real-time Audio and Tactical Board Synchronization**: Sub-500ms pipeline architecture.
  - **ADR-0013: Frontend Microfrontend Architecture**: Modular UI decomposition.

## Scope of Work & Implementation Plan
1. **Session Lobby Readiness & Stand-In Synchronization (`frontend/src/runefoble-app.ts`)**:
   - Add `@toggle-readiness=${(e: CustomEvent) => this.handleToggleReadiness(e)}`:
     - Update `this.lobbyParticipants` state.
     - Broadcast `{ type: 'player_readiness', userId: e.detail.userId, isReady: e.detail.isReady }` over the session WebSocket.
   - Add `@toggle-stand-in=${(e: CustomEvent) => this.handleToggleStandIn(e)}`:
     - Update `this.lobbyParticipants` state and broadcast `{ type: 'player_stand_in', userId: e.detail.userId, isAbsent: e.detail.isAbsent }`.
2. **Tactical Board WebSocket & Event Mesh Integration (`frontend/src/runefoble-app.ts`)**:
   - Pass `websocketUrl` to `<runefoble-board>` using the active session WebSocket URI.
   - Add event listeners on `<runefoble-board>`:
     - `@token-action`: Handle radial menu actions (`attack`, `cast`, `inspect`, `ready`).
     - `@aoe-place`: Broadcast AoE geometric placement over WebSocket to all party members.
     - `@spell-vfx-triggered`: Propagate particle bloom effects across clients.
     - `@confirm-ghost`: Finalize spoken ghost movement path.
   - Dynamically supply `.cols` and `.rows` from loaded session/map metadata rather than hardcoding `8x8`.
3. **Register Default Tabletop Plugins (`frontend/src/components/plugins/plugin_registry.ts`)**:
   - Initialize standard default plugins:
     - Slot `hud-widget`: Mount `<runefoble-initiative-tracker>` and `<runefoble-soundscape-controls>`.
     - Slot `dice-panel`: Mount `<runefoble-dice-roller>` and `<runefoble-dice-tray-3d>`.
     - Slot `sidebar-tool`: Mount `<runefoble-combat-reaction-prompt>` and, when user is DM, `<runefoble-dm-whisper-bar>` and `<runefoble-dm-trap-controls>`.
4. **Expand WebSocket Event Dispatching (`frontend/src/runefoble-app.ts`)**:
   - In `manageWebSocketLifecycle.socket.onmessage`, handle:
     - `dice_rolled`: Update dice roller and trigger 3D tray physics roll.
     - `turn_advanced`: Update active combatant in initiative tracker.
     - `aoe_placed`: Render AoE template on `<runefoble-board>`.
     - `spell_vfx`: Trigger WebGL particle bloom on `<runefoble-board>`.
     - `dm_whisper`: Feed private whisper channel in `<runefoble-dm-whisper-bar>`.
5. **Blackbox TDD Tests**:
   - Author `tests/test_blackbox_vtt_websocket_mesh.py` asserting multi-client WebSocket event broadcasting (readiness, dice rolls, turns, AoE placement).
   - Update `frontend/test/app-shell.test.ts` to verify plugin slots and VTT event bindings.

## INVEST Criteria Evaluation
- **Independent (I)**: Focuses on the active session view and real-time event pipeline.
- **Negotiable (N)**: Plugin placement and default slot arrangements can be tuned.
- **Valuable (V)**: Transforms the tabletop from a static canvas into an interactive, multi-user collaborative VTT with live dice, turns, and audio.
- **Estimable (E)**: Components and event types are well-defined in existing microfrontends.
- **Small (S)**: Confined to App Shell VTT wiring, plugin registry seeding, and WebSocket handler expansion.
- **Testable (T)**: Tested with WebSocket blackbox client simulations and Lit event tests.

## Definition of Done
1. Checking "Ready" or "Absent" in the session lobby synchronizes across connected clients in real time.
2. Default plugin slots (`hud-widget`, `dice-panel`, `sidebar-tool`) render active tools (initiative tracker, dice tray, DM controls) rather than blank space.
3. Tactical board radial menu actions and AoE placements broadcast to peer clients over WebSocket.
4. Dice rolls, turn advancements, and spell VFX update live without page reload.
5. All tests pass with zero regressions.
