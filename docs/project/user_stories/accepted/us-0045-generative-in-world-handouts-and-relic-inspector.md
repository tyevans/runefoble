---
id: '0045'
title: Generative In-World Handouts, Wax Seals and 3D Relic Inspector
status: Accepted
created: 2026-09-26
persona: Rowan (The Chronicler & Worldbuilding Artisan)
feature: FEAT-LRE-02
governing_prd: PRD-0015
---

# US-0045 — Generative In-World Handouts, Wax Seals and 3D Relic Inspector

## Governing PRD
- [`PRD-0015: Generative Diegetic Handouts, 3D Relic Inspector & Printable Tabletop Forge`](../../product/accepted/prd-0015-generative-handouts-relic-inspector-and-printable-forge.md)

## User Story

**As a** lore enthusiast and worldbuilding artisan,  
**I want** to generate diegetic in-world artifacts—such as weathered parchment letters with breakable wax seals, decipherable runic ciphers, and interactive 3D rotating relics—  
**So that** discovering ancient clues and magical loot feels like inspecting real physical treasures rather than reading generic database modals.

## Scenario 1: Unsealing an Ancient Forged Letter
```gherkin
Given the DM or player specifies a story prompt for an intercepted letter
When the artifact engine generates the diegetic handout
Then a photorealistic weathered parchment appears with custom calligraphy and a crimson wax seal
And when a player clicks the seal, a dynamic wax-cracking animation and haptic audio sound plays
And breaking the seal reveals the hidden body text and any secret UV-reactive invisible ink runes.
```

## Scenario 2: 3D Relic Inspection & Inscription Reading
```gherkin
Given the party discovers the "Amulet of the Sunken Spire"
When Rowan opens the relic inspector
Then a real-time WebGL canvas renders the 3D rotating amulet with realistic metal and gemstone shaders
And Rowan can rotate, zoom, and inspect microscopic etched runes on the reverse casing
And clicking the runes emits a translation prompt to The Watcher or Campaign Lore service.
```
