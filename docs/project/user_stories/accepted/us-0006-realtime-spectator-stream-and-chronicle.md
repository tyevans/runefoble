---
id: 0006
title: Real-Time Spectator Stream and Chronicle
status: Accepted
created: 2026-09-25
persona: Devon (The Live Streamer / Spectator)
feature: FEAT-BRD-01, FEAT-VOX-01
governing_prd: PRD-0011
---

# US-0006 — Real-Time Spectator Stream and Chronicle

## Governing PRD
- [`PRD-0011: Live Spectator Studio & Two-Way Audience Interactivity`](../../product/accepted/prd-0011-live-spectator-studio-and-audience-interactivity.md)

## User Story

**As a** tabletop streamer or online spectator,
**I want** a dedicated clean-overlay web view of the tactical board and live Watcher Chronicle feed,
**So that** my stream audience can follow token animations, dice rolls, and atmospheric story narration in real time without seeing private DM controls.

## Scenario: Connecting as Spectator
```gherkin
Given a live campaign session "camp1" is active
When Devon opens the spectator URL with a spectator auth token
Then the tactical board displays tokens, fog of war, and animations over WebSocket
And the Watcher Chronicle feed shows transcribed player speech and DM narrative
And token dragging and dice rolling inputs are disabled for the spectator.
```
