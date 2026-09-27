---
id: '0055'
title: Generative Character Wardrobe, Emotion & State Portrait Gallery
status: Accepted
created: 2026-09-26
persona: Nadia (The Expressive Thespian & Performer)
feature: FEAT-EXP-03
governing_prd: PRD-0016
---

# US-0055 — Generative Character Wardrobe, Emotion & State Portrait Gallery

## Governing PRD
- [`PRD-0016: Personal Character Leitmotifs, Wardrobe Gallery & Kinetic WebGL Spell VFX`](../../product/accepted/prd-0016-character-leitmotifs-and-kinetic-spell-vfx.md)

## User Story

**As an** expressive roleplayer,  
**I want** my character portrait and board token to dynamically adapt their attire, emotional expression, and physical condition to active gameplay states (such as bloodied injuries at low HP, condition overlays, and generative wardrobe changes for royal balls or arctic expeditions),  
**So that** my character's visual appearance naturally mirrors the unfolding dramatic narrative without manually re-uploading avatars.

## Scenario 1: Automatic Bloodied & Affliction Portrait Overlays
```gherkin
Given Nadia's character drops below 50% HP during intense combat
When the character sheet updates HP state
Then the character sheet portrait and token badge update within 200ms with a subtle bloodied vignette and grimacing emotion overlay
And when Nadia gains the "Poisoned" condition, a sickly green aura and distressed facial expression tint her active portrait.
```

## Scenario 2: Generative Thematic Wardrobe Switching
```gherkin
Given the party attends an undercover royal masquerade ball in Session 14
When Nadia selects "Generate Ball Masquerade Attire" in her character sheet gallery
Then the asset forge synthesizes an ornate masquerade gown variation preserving her character's facial features and color palette
And saves the variant to Silo S3 with instantaneous token portrait synchronization across all party members.
```
