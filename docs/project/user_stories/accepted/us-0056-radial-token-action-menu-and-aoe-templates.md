---
id: '0056'
title: Radial Token Action Menu & Rotatable AoE Spell Templates
status: Accepted
created: 2026-09-26
persona: Marcus (The Casual Adventurer & Tactician)
feature: FEAT-UI-06
governing_prd: PRD-0013
---

# US-0056 — Radial Token Action Menu & Rotatable AoE Spell Templates

## Governing PRD
- [`PRD-0013: Immersive & Intuitive Frontend Experience with Tactile Board Kinematics`](../../product/accepted/prd-0013-immersive-and-intuitive-frontend-experience.md)

## User Story

**As a** tabletop player and tactical combatant,  
**I want** a contextual circular dial for one-tap token actions and rotatable geometric AoE spell templates with live target intersection highlighting,  
**So that** I can trigger common combat maneuvers (attack, dodge, dash, cast) and position spell templates precisely without navigating complex nested menus.

## Scenario 1: Quick Radial Action Invocation
```gherkin
Given Marcus clicks or taps his character token on the tactical board
When the radial action menu blooms outwards in 120ms with Bauhaus geometric icons
Then Marcus can execute "Dodge", "Dash", or "Melee Strike" with a single click or directional flick
And the selected action dispatches directly to the session turn manager.
```

## Scenario 2: Rotatable Cone and Sphere AoE Placement
```gherkin
Given Marcus selects a "Burning Hands 15-foot Cone" spell template
When Marcus drags the template origin to his token and drags the rotational handle towards enemy goblins
Then the board dynamically computes square/hex intersection calculations at 60fps
And highlights all affected monster tokens with glowing red targeting halos before confirming the cast.
```
