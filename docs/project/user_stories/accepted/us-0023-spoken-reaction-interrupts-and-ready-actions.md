---
id: 0023
title: Spoken Reaction Interrupts and Ready-Action Triggers
status: Accepted
created: 2026-09-25
---

# US-0023 — Spoken Reaction Interrupts and Ready-Action Triggers

## User Story

**As a** player watching an enemy's turn unfold (Marcus),  
**I want to** shout reactions like "I cast Shield!" or set ready-action triggers,  
**So that** tactical interrupts resolve dynamically without breaking the live combat flow.

## Acceptance Criteria

1. **Reaction Turn Interruption**: Shouting recognized reaction phrases ("Shield!", "Counterspell!", "Opportunity Attack!") immediately halts the active turn resolution.
2. **Ready-Action Conditional Registry**: Verbal declarations ("I ready my crossbow to shoot if the goblin steps into the hallway") register a conditional event in `game_session`.
3. **Automated Trigger Firing**: When the specified spatial or turn condition is met, the system prompts the reacting player and executes the readied action.
