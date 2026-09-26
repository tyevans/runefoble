---
id: 0005
title: Absentee Session Chronicle and Audio Recap
status: Accepted
created: 2026-09-25
persona: Sarah (The Absent Player)
feature: FEAT-WAT-05
---

# US-0005 — Absentee Session Chronicle and Audio Recap

## User Story

**As an** absent player returning for the subsequent gaming session,  
**I want** The Watcher to generate an audio and text recap of everything my character did while piloted by the AI stand-in (including the effects of any penalties like "drunk" or "foolishness"),  
**So that** I am immediately brought up to speed on party progress and can laugh along with my friends at my character's unintended shenanigans.

## Scenario: Listening to Session Recap
```gherkin
Given Sarah was marked absent for Session 14
And her character Kyra was assigned the "Drunk" penalty
When Sarah opens the campaign lobby for Session 15
Then The Watcher presents an "Absentee Recap" modal with audio playback
And the narration humorously recounts: "Kyra boldly charged the goblin barricade, swaying merrily, and cast Bless with dwarven ale still sloshing in her flagon"
And her character sheet updates with any HP loss, spell slot consumption, or loot acquired.
```
