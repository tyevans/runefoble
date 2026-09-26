---
id: '0013'
title: Immersive & Intuitive Frontend Experience with Tactile Board Kinematics
status: Shaped
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
