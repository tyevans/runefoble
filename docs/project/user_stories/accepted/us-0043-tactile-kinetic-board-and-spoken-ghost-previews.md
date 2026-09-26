---
id: '0043'
title: Tactile Kinetic Board Interaction and Spoken Ghost Previews
status: Accepted
created: 2026-09-25
persona: Evelyn (The Dungeon Master / Storyteller)
feature: FEAT-UI-04
governing_prd: PRD-0013
---

# US-0043 — Tactile Kinetic Board Interaction and Spoken Ghost Previews

## Governing PRD
- [`PRD-0013: Immersive & Intuitive Frontend Experience with Tactile Board Kinematics`](../../product/accepted/prd-0013-immersive-and-intuitive-frontend-experience.md)

## User Story

**As a** Dungeon Master running high-stakes combat encounters,  
**I want** tactile drag-and-drop token physics with automatic route step-counters and real-time semi-transparent "ghost previews" of spoken actions,  
**So that** players can visually verify and adjust their movements and spell areas before committing to the shared game state.

## Scenario 1: Spoken Command Ghosting and Instant Confirmation
```gherkin
Given a combat encounter is active
When a player speaks "Valeros moves 3 squares north and attacks the Orc Raider"
Then within 200ms a semi-transparent ghost token appears at the target square
And an animated targeting trajectory line links Valeros to the Orc Raider
And the player can speak "Confirm" or click the ghost to commit the movement.
```

## Scenario 2: Token Kinematics & Waypoint Measuring
```gherkin
Given a player drags their character token across the tactical board
Then the token animates with subtle inertia and snap-to-grid collision
And a dynamic measurement ruler displays the path distance in 5-foot increments
And difficult terrain and hazard squares highlight automatically along the route.
```
