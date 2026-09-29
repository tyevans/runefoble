---
id: '0013'
title: Immersive & Intuitive Frontend Experience with Tactile Board Kinematics
status: Accepted
created: 2026-09-25
---

# PRD-0013 — Immersive & Intuitive Frontend Experience with Tactile Board Kinematics

## Who this is for

Tabletop roleplaying players, Game Masters, and live-stream audiences seeking a high-tactility, low-friction virtual tabletop that feels like handling physical miniatures on a living, animated game board.

## What the person cannot do today

Existing virtual tabletops (Roll20, Foundry, Owlbear Rodeo) suffer from clunky, menu-heavy web interfaces:
- Moving a token requires tedious clicking, measuring with awkward ruler tools, and navigating deeply nested floating menus.
- Voice commands and board updates operate in disconnected silos; speaking does not provide visual confirmation before board mutation commits.
- Lighting and fog-of-war are either static grey overlays or slow polygon raytracers that chug on laptops and mobile tablets.
- In-person groups playing with a tablet flat on the table struggle with tiny desktop UI targets and missing touch gestures.

## What good looks like

1. **Tactile Board Kinematics & Momentum**:
   - Tokens behave like physical wooden or stone miniatures with subtle inertia, spring dampening, and snap-to-grid collision.
   - Dragging a token projects an automatic movement path with step counters, difficult terrain movement costs, and clear hazard warnings.
2. **Zero-Friction Spoken Command Ghosting**:
   - When a player speaks a command ("Valeros moves two steps east and attacks the goblin"), a semi-transparent "ghost token" and target reticle appear on the board within 200ms.
   - The player or DM can cancel or adjust the ghost with a single tap/click before the action executes into the persistent game state.
3. **Radial Ergonomics & Contextual Micro-Interactions**:
   - Tapping or clicking any token summons a clean geometric radial wheel with primary actions (Move, Attack, Cast Spell, Dash, Inspect, Conditions) tailored to character capabilities.
   - Area-of-effect (AoE) spell templates (cones, spheres, lines, cubes) can be picked up and oriented with tactile rotation rings, highlighting affected enemy/ally tokens in real time.
4. **Atmospheric Audiovisual Immersion**:
   - Living tactical maps with dynamic torchlight flicker, weather particles (rain, falling embers, crypt mist), and smooth shroud dissipation upon exploration.
   - 3D geometric dice physics rolling directly onto the board or in a dedicated Bauhaus dice tray with spatial collision acoustics.
   - Automatic narrative camera focal zooms when The Watcher describes dramatic beats or boss encounters.
5. **Unified Role Workspaces**:
   - One-touch toggle between Player HUD (focused board + quick spell/action shortcuts), GM God-Mode (fog paintbrush, hidden notes, monster spawner drawer), and Spectator Broadcast View.

## What this does not do

- It does not turn Runefoble into an automated video game; players and DMs retain full manual override and narrative discretion.
- It does not require high-end GPU hardware; rendering runs at a consistent 60fps on standard browser canvas/SVG engines.
- It does not hide mechanical transparency; all dice rolls, modifiers, and distance formulas remain clearly visible and auditable.

## What it costs at scale

- Multi-token physics and real-time raycasting require optimized WebGL/Canvas rendering loops to avoid battery drain on portable tablets.
- Real-time ghost preview state over WebSockets requires compact binary/JSON delta frames to prevent network jitter under high player counts.

## Checkable Outcomes

1. Token drag-and-drop renders with responsive kinematics maintaining 60fps frame rate during movement animations on modern browsers.
2. Spoken voice commands generate a visual ghost preview and trajectory line on the board in under 200ms from speech-to-intent resolution.
3. Radial action wheel opens on token interaction in <50ms with touch targets measuring at least 44x44px for tablet accessibility.
4. AoE spell targeting templates accurately compute and visually highlight intersecting token coordinates in real time.
5. Canvas rendering performance remains smooth with zero console errors across all themes (Bauhaus, Dark Fantasy, Parchment, Cyber Rune) and color modes.

## Linked User Stories
- [`US-0004: Isolated Component Development in Storybook`](../../user_stories/accepted/us-0004-developer-tests-component-in-storybook.md)
- [`US-0013: Zanzibar Campaign Role Authorization Gateway Enforcement`](../../user_stories/accepted/us-0013-gateway-zanzibar-authorization.md)
- [`US-0016: Themable Frontend Design System with Bauhaus Modernist Default`](../../user_stories/accepted/us-0016-themable-frontend-with-bauhaus-default.md)
- [`US-0041: Settings Modal with Dark/Light/System Mode & Integrated Theme Switcher`](../../user_stories/accepted/us-0041-settings-modal-and-appearance-mode-switching.md)
- [`US-0042: Accessible Dark and Light Mode Theming Invariants Across Components`](../../user_stories/accepted/us-0042-accessible-dark-and-light-mode-theming.md)
- [`US-0043: Tactile Kinetic Board Interaction and Spoken Ghost Previews`](../../user_stories/accepted/us-0043-tactile-kinetic-board-and-spoken-ghost-previews.md)

## Implementing Backlog Tasks
- [`TASK-0006: Voice DSP Audio Conditioning and Slurred Speech Synthesis`](../../backlog/complete/0006-voice-dsp-conditioning-filters.md)
- [`TASK-0043: Frontend Microfrontend Component Styles and Subview Decomposition`](../../backlog/complete/0043-frontend-microfrontend-component-styles-and-subview-decomposition.md)
- [`TASK-0061: Tactical Board, Autonomous DM, and Voice Controls Microfrontend Styles Decomposition`](../../backlog/complete/0061-board-autonomous-dm-and-voice-controls-ui-styles-decomposition.md)
- [`TASK-0072: Immersive & Intuitive Frontend Experience Product Requirements Definition (PRD)`](../../backlog/complete/0072-frontend-experience-vision-prd.md)
- [`TASK-0073: Frontend Settings Modal with Dark/Light/System Mode & Integrated Theme Switcher`](../../backlog/complete/0073-frontend-settings-modal-and-theme-mode-orchestration.md)
- [`TASK-0074: Design System Dark and Light Mode Color Tokens & Cross-Component Contrast Invariants`](../../backlog/complete/0074-dark-light-mode-color-tokens-and-component-contrast.md)
- [`TASK-0084: Tactile Board Kinematics and Spoken Ghost Previews`](../../backlog/complete/0084-tactile-board-kinematics-and-spoken-ghost-previews.md)
- [`TASK-0086: Settings Modal Tab Panels and Sub-Controllers Modular Decomposition`](../../backlog/complete/0086-settings-modal-tabs-and-controllers-decomposition.md)
- [`TASK-0088: Microfrontends Blackbox Test Suite Modular Decomposition`](../../backlog/complete/0088-microfrontends-test-suite-decomposition.md)
- [`TASK-0485: Tactile Board Atmospheric Weather Particles and Torchlight Flicker Overlay`](../../backlog/proposed/0485-tactile-board-atmospheric-weather-and-torchlight-flicker-overlay.md)
- [`TASK-0486: Tactile Board Spoken Ghost Preview Interactive Fine-Tuning and Confirmation`](../../backlog/proposed/0486-tactile-board-spoken-ghost-preview-interactive-fine-tuning-and-confirmation.md)
- [`TASK-0487: Tactile Board GM God-Mode Workspace and Fog-of-War Paintbrush`](../../backlog/proposed/0487-tactile-board-gm-god-mode-workspace-and-fog-paintbrush.md)
- [`TASK-0488: Tactile Board Atmosphere and GM Workspace Frontdoor Blackbox Test Suite`](../../backlog/proposed/0488-tactile-board-atmosphere-and-gm-workspace-frontdoor-blackbox-test-suite.md)

