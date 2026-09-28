---
id: '0074'
title: Interactive Mobile Web Tavern and Casino Minigames Suite
status: Accepted
created: 2026-09-27
persona: Kip (The Mobile Barfly & Social Gambler)
feature: FEAT-SET-03
governing_prd: PRD-0024
---

# US-0074 — Interactive Mobile Web Tavern and Casino Minigames Suite

## Governing PRD
- [`PRD-0024: Settlement Haven Builder, Living Urban Ecosystem & Mobile Web Minigames`](../../product/accepted/prd-0024-settlement-haven-builder-and-mobile-minigames.md)

## User Story

**As a** mobile tabletop player resting at an establishment,  
**I want** to launch and play real-time interactive minigames (including tavern darts, pool, Liar's Dice, roulette, and craps) straight from my smartphone web browser without installing an app,  
**So that** my friends and I can engage in tactile, responsive social gambling, casual wagering, and friendly competition while our characters relax in taverns and gaming halls.

## Scenario 1: Throwing Darts and Shooting Pool in a Tavern from Phone Browser
```gherkin
Given Kip enters the "Salty Siren" tavern on his phone browser at `#/campaigns/:id/town/taverns/1`
When Kip selects "Play Darts" and wagers 5 silver pieces with a party member
Then a touch-drag dart canvas loads with smooth trajectory physics, wind variation, and haptic feedback
And Kip's flick gesture tosses the dart toward the dartboard, updating scores in real time
And when switching to the billiards table, multi-touch cue aiming and 2D ball collisions synchronize across players.
```

## Scenario 2: High-Stakes Casino Roulette and Street Bones Craps
```gherkin
Given Kip and the party visit the "Gilded Serpent Casino" in the high district
When Kip joins the Dragon Craps table and places a wager on the Pass Line
Then Kip performs a two-finger flick gesture to tumble physical 3D dice across the felt tray
And dice rest results are computed and synchronized to all connected players within 100ms
And winning payouts are automatically credited to player character coin purses with victory audio cues.
```
