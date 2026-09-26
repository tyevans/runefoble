---
id: 0034
title: Agnostic TTRPG Ruleset Schemas and System Expansion
status: Accepted
created: 2026-09-25
---

# US-0034 — Agnostic TTRPG Ruleset Schemas and System Expansion

## User Story

**As an** indie game designer and plugin developer (Alex),  
**I want to** define custom character sheet schemas and rule mechanisms beyond standard d20 fantasy,  
**So that** Runefoble supports diverse TTRPG systems (e.g. Call of Cthulhu sanity meters, Blades in the Dark progress clocks).

## Acceptance Criteria

1. **System-Agnostic Sheet Definitions**: Character sheets support arbitrary user-defined attribute blocks, pools, and condition tags via JSONSchema.
2. **Dynamic Dice Expressions**: Dice roller parses non-standard dice mechanics (e.g. dice pools, exploding dice, percentile checks).
3. **Watcher Rules Adaptability**: The Watcher’s intent prompt and validation accept the active game system schema as context.
