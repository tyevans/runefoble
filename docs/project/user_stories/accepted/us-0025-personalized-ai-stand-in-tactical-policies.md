---
id: 0025
title: Personalized AI Stand-In Tactical Policies and Playstyle Guardrails
status: Shipped
created: 2026-09-25
governing_prd: PRD-0002
---

# US-0025 — Personalized AI Stand-In Tactical Policies and Playstyle Guardrails

## Governing PRD
- [`PRD-0002: Missing Player AI Stand-In with Mimicry and Absence Costs`](../../product/accepted/prd-0002-missing-player-ai-stand-in-with-penalties.md)

## User Story

**As a** player who must occasionally miss a session (Sarah),  
**I want to** configure tactical guardrails and behavioral preferences for my AI stand-in,  
**So that** my Cleric protects my allies and preserves high-level spell slots according to my playstyle.

## Acceptance Criteria

1. **Stand-In Guardrail Profiles**: Sarah can set behavioral priorities (e.g. "Save Level 3 slots for Revivify", "Prioritize healing Marcus if under 30% HP", "Avoid frontline melee").
2. **Dynamic Decision Weighting**: The stand-in AI reasoning graph evaluates player-specified guardrails before selecting actions.
3. **Humorous Penalty Adaptation**: When DM penalties (e.g. "drunk") are active, the stand-in maintains tactical intent while comically flavoring dialogue and actions.
