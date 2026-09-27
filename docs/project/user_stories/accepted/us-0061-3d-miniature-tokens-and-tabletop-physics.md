---
id: '0061'
title: 3D Miniature Tokens & WebGL Tabletop Physics
status: Accepted
created: 2026-09-26
persona: Devon (The Live Streamer & Spectator Host)
feature: FEAT-BRD-06
governing_prd: PRD-0013
---

# US-0061 — 3D Miniature Tokens & WebGL Tabletop Physics

## Governing PRD
- [`PRD-0013: Immersive & Intuitive Frontend Experience with Tactile Board Kinematics`](../../product/accepted/prd-0013-immersive-and-intuitive-frontend-experience.md)

## User Story

**As a** tabletop streamer or visual player,  
**I want** 3D WebGL miniature tokens with physical dice rolling and collision physics on the tactical board,  
**So that** high-stakes combat encounters have tactile, visually spectacular tabletop presence.

## Scenario 1: Physical Dice Collision with 3D Miniatures
```gherkin
Given Marcus rolls a d20 attack check on the 3D tactical board
When the dice physics simulation resolves the dice roll across the terrain
Then the tumbling dice bounce realistically off walls, pillars, and miniature token bases
And settle on the numerical result with an acoustic dice tray clatter sound effect.
```

## Scenario 2: Miniature Knockback and Elevation Physics
```gherkin
Given a minotaur performs a charging bull-rush attack on a player character miniature
When the attack succeeds with 10 feet of knockback
Then the 3D miniature token slides back along the grid with momentum and friction damping
And falls accurately down terrain elevation steps with ragdoll balance recovery.
```
