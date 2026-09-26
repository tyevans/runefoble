---
id: '0050'
title: Collaborative Campaign Atlas and Multi-Layered Living Codex
status: Accepted
created: 2026-09-26
persona: Rowan (The Chronicler & Worldbuilding Artisan)
feature: FEAT-LRE-04
---

# US-0050 — Collaborative Campaign Atlas and Multi-Layered Living Codex

## User Story

**As a** campaign chronicler and collaborative storyteller,  
**I want** a shared multi-layered regional and world atlas with interactive chronological timeline pins, faction control overlays, and collaborative player journal codices,  
**So that** the entire party can collectively document, explore, and shape the evolving geopolitical history of our shared campaign world.

## Scenario 1: Placing a Chronological Timeline Pin
```gherkin
Given the party liberates the "Silverkeep Garrison" in Session 12
When Rowan opens the Campaign Atlas and places a milestone pin on the Silverkeep territory
Then the pin records the session date, participant characters, and key decisions
And links directly to the generated session chronicle and redstring lore graph
Allowing any party member to filter the world map by timeline eras.
```

## Scenario 2: Collaborative Player Codex & Secret Notes
```gherkin
Given Rowan writes a secret lore theory regarding the "Order of the Obsidian Veil"
When Rowan marks the codex entry as "Shared with Party" or "Private to Rowan"
Then SpiceDB Zanzibar permissions enforce read access accordingly
And when shared, all players see the illuminated codex entry with inline entity cross-references
Powered by the Campaign Lore redstring knowledge base.
```
