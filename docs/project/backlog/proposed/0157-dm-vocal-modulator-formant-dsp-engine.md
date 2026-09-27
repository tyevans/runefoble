---
id: '0157'
title: DM Live Vocal Modulator and Real-Time NPC Formant DSP Engine
status: Proposed
created: 2026-09-26
dependencies:
- TASK-0006
- TASK-0021
- TASK-0065
governing_adrs:
- ADR-0002
- ADR-0003
governing_prds:
- PRD-0004
governing_stories:
- US-0020
target_release: 0.6.0
---

# TASK-0157: DM Live Vocal Modulator and Real-Time NPC Formant DSP Engine

## Status
Proposed

## Summary
Implement real-time DSP pitch and formant shift filters in `services/voice_agent/` allowing DMs to apply NPC vocal transformations ("Ancient Dragon", "Goblin Skulker", "Celestial Spirit") to outgoing WebAudio streams with <50ms processing latency.

## Problem Statement
Voicing diverse NPCs across marathon sessions causes severe vocal strain for DMs. Adding digital signal processing for formant frequency manipulation and pitch scaling directly into the voice pipeline enables rich character portrayal without physical fatigue.

## Governing Architecture & ADRs
- **ADR-0002: Event-Driven Watcher Gameplay Orchestration**: Real-time audio pipeline integration.
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean module layout in `services/voice_agent/`.

## Scope of Work
1. **Formant & Pitch Modulation Nodes**:
   - WebAudio/NumPy DSP filter chains for formant scaling, resonance shifting, and pitch octave offsets (< 160 lines).
2. **NPC Vocal Preset Profiles**:
   - Preset configurations for common creature archetypes (deep dragon resonance, screeching goblin, ethereal echo) (< 120 lines).
3. **Low Latency Pipeline Hook**:
   - Integrate formant DSP into WebRTC audio track streaming with <50ms latency.
4. **Frontdoor Verification**:
   - Blackbox tests validating preset activation and audio DSP transformation parameters.
