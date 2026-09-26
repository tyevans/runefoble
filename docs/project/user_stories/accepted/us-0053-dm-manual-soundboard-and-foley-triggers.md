---
id: 0053
title: DM Manual Soundboard Triggers and Tactical Foley Overrides
persona: Evelyn (DM)
status: Accepted
created: 2026-09-26
governing_prd: PRD-0010
---

# US-0053 — DM Manual Soundboard Triggers and Tactical Foley Overrides

## Governing PRD
- [`PRD-0010: Adaptive Soundscape, Environmental Foley & Combat Scoring`](../../product/accepted/prd-0010-adaptive-soundscape-foley-and-tension-scoring.md)

## Persona
Evelyn (DM)

## User Story

**As a** Dungeon Master orchestrating high-tension narrative climaxes,  
**I want to** trigger manual soundboard foley cues (thunder, dungeon door slams, blade parries) and override ambient tension levels from my DM screen,  
**So that** I have total theatrical control over the session soundscape alongside The Watcher's automated background scoring.

## Acceptance Criteria

1. **One-Click Foley Cues**: DM interface exposes low-latency tactical soundboard buttons triggering spatialized SFX cues via WebAudio within 100ms.
2. **Dynamic Tension Override**: A tactile slider allows the DM to force combat tension states (Calm, Suspense, Combat, Boss Battle), overriding automated algorithmic tension scores.
3. **WebAudio Ducking Coordination**: Triggered foley or voice announcements duck background ambient music stems by -12dB with smooth 200ms ease-in/ease-out crossfades.
4. **WebSocket Fanout**: Sound trigger events broadcast across all player clients to synchronize multi-ear acoustic playback in real time.
