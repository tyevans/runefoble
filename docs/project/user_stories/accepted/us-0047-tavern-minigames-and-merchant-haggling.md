---
id: '0047'
title: Interactive Tavern Minigames, Gambling and Personality-Driven Merchant Haggling
status: Accepted
created: 2026-09-26
persona: Bram (The Tinkerer & Downtime Crafter)
feature: FEAT-DWN-03
---

# US-0047 — Interactive Tavern Minigames, Gambling and Personality-Driven Merchant Haggling

## User Story

**As a** social roleplayer and tactician visiting town settlements,  
**I want** interactive tavern minigames (such as Liar's Dice, card wagering, and drinking contests) alongside personality-driven merchant bartering with dynamic negotiation temperaments,  
**So that** visits to town taverns and bazaars are lively, participatory social adventures rather than transactional menu clicks.

## Scenario 1: Playing Liar's Dice in the Tavern
```gherkin
Given Bram's character visits the "Drunken Wyvern" tavern
When Bram challenges an NPC pirate to a game of Liar's Dice with a 10 gold wager
Then a 3D cup and dice wagering interface opens in the tavern microfrontend
And the players take turns bluffing, raising bids, and challenging dice counts
And on victory, the wagered gold is credited and a victory voice bark plays.
```

## Scenario 2: Dynamic Merchant Haggling with Temperament State
```gherkin
Given Bram negotiates with a dwarven blacksmith who possesses a "stubborn but greedy" temperament
When Bram uses persuasion dialogue and counters the initial 50 gold quote with 35 gold
Then The Watcher evaluates Bram's charisma modifier and social offer
And either adjusts the merchant's mood meter or counters with 42 gold
Emitting an in-character merchant voice line reflecting the negotiation outcome.
```
