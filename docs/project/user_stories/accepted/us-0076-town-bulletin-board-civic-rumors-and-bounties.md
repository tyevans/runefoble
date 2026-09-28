---
id: '0076'
title: Civic Bulletin Board, Town Rumor Network, and Bounty Proclamations
status: Accepted
created: 2026-09-27
persona: Sam (The Table Spectator & Casual Companion)
feature: FEAT-SET-05
governing_prd: PRD-0024
---

# US-0076 — Civic Bulletin Board, Town Rumor Network, and Bounty Proclamations

## Governing PRD
- [`PRD-0024: Settlement Haven Builder, Living Urban Ecosystem & Mobile Web Minigames`](../../product/accepted/prd-0024-settlement-haven-builder-and-mobile-minigames.md)

## User Story

**As an** adventurer or casual spectator browsing a community gathering spot,  
**I want** to interact with a cork-and-parchment town bulletin board to inspect bounties, uncover local rumors, decipher hidden tavern flyers, and post party contract requests,  
**So that** communal town squares and taverns serve as vibrant narrative nexus points that tie together local establishment happenings, player goals, and emerging campaign storylines.

## Scenario 1: Inspecting Bounties and Rumors on the Town Square Board
```gherkin
Given Sam scans the town square QR code on his mobile phone to join the session as a spectator
When Sam clicks on the Town Bulletin Board located at the crossroads plaza
Then an interactive bulletin board displays pinned parchment notes with wax seals and varied handwriting fonts
And Sam can tap individual notices to read monster bounties, lost heirloom rewards, and town gossip
Emitting subtle paper rustling audio feedback on touch interaction.
```

## Scenario 2: Posting Adventurer Contracts and Deciphering Hidden Ciphers
```gherkin
Given party member Kip discovers a coded thieves' cant flyer pinned behind an official tax notice
When Kip solves the rotational cipher mini-game on his phone screen
Then the hidden text reveals a secret late-night rendezvous at the Gilded Serpent Casino back alley
And Kip pins a counter-notice offering mercenary protection services to the local merchant guild
Persisting the custom contract to the settlement's bulletin board aggregate for other players to view.
```
