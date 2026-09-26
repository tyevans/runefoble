---
id: 0024
title: Natural Speech Equipment Swapping and Hands-Free Wake-Word
status: Accepted
created: 2026-09-25
governing_prd: PRD-0006
---

# US-0024 — Natural Speech Equipment Swapping and Hands-Free Wake-Word

## Governing PRD
- [`PRD-0006: Character Sheet Inventory, Equipment & Condition Aggregation`](../../product/accepted/prd-0006-digital-character-sheet-inventory-and-conditions.md)

## User Story

**As a** player engaged in natural party conversation (Marcus),  
**I want to** swap weapons and quaff potions by speaking naturally with hands-free wake-word filtering,  
**So that** I can banter casually with friends without accidentally issuing game commands.

## Acceptance Criteria

1. **Wake-Word Filtering**: Speech commands are triggered via hotword ("Hey Watcher...") or smart conversational intent detection, ignoring casual party banter.
2. **Spoken Item Management**: Phrases such as "I sheath my broadsword, draw my silver dagger, and drink a potion" update equipped inventory slots and consumable quantities.
3. **Auditory Earcon Confirmation**: A low-latency sound cue (e.g. blade unsheathing) confirms command registration within 150ms.
