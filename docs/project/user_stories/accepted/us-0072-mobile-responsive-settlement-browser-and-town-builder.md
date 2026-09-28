---
id: '0072'
title: Mobile-Responsive Settlement Browser and Town Haven Builder
status: Accepted
created: 2026-09-27
persona: Mayor Theron (The Civic Architect & Frontier Mayor)
feature: FEAT-SET-01
governing_prd: PRD-0024
---

# US-0072 — Mobile-Responsive Settlement Browser and Town Haven Builder

## Governing PRD
- [`PRD-0024: Settlement Haven Builder, Living Urban Ecosystem & Mobile Web Minigames`](../../product/accepted/prd-0024-settlement-haven-builder-and-mobile-minigames.md)

## User Story

**As a** civic planner and campaign adventurer,  
**I want** to browse and build settlement havens directly from mobile web browsers and desktop screens, selecting from geographic biomes, town scales (hamlet, village, market town, city, metropolis), and zoning districts,  
**So that** our party can establish, expand, and govern a persistent frontier settlement whose layout and industries naturally reflect its surrounding geographic landscape.

## Scenario 1: Founding a Frontier Haven on Mobile Web
```gherkin
Given Mayor Theron accesses the Runefoble campaign portal from a mobile smartphone browser
When Theron navigates to the settlement builder view and selects "Found New Haven"
Then the builder presents biome templates (River Confluence, Mountain Pass, Coastal Haven, Forest Edge)
And Theron designates the settlement as a "Village" scale with an agricultural commons and defensive palisade
And the settlement aggregate is initialized with core civic stats, district zones, and spatial coordinates.
```

## Scenario 2: Upgrading Settlement Scale and Unlocking Specialized Districts
```gherkin
Given the party's settlement "Oakhaven" has accumulated sufficient civic prosperity and population
When Theron upgrades the settlement tier from "Village" to "Market Town"
Then the interactive town map expands to reveal walled perimeters, a paved central plaza, and specialized zoning slots
And the system unlocks artisan quarters, fortified watch barracks, and commercial establishment licenses
Emitting a settlement upgrade domain event that notifies all active campaign participants.
```
