---
id: 0050
title: Dynamic Soundscape & Adaptive Audio Microservice
status: Proposed
created: 2026-09-25
dependencies: [TASK-0006, TASK-0021, TASK-0025]
governing_adrs: [ADR-0007, ADR-0010]
target_release: 0.3.0
---

# TASK-0050: Dynamic Soundscape & Adaptive Audio Microservice

## Status
Proposed

## Summary
Scaffold a new bounded context `services/soundscape` responsible for dynamic background music stem mixing, spatial environmental foley, and synchronized tactical sound effects based on encounter tension.

## Problem Statement
Tabletop audio immersion currently suffers because `voice_agent` only handles spoken dialogue. DMs must manually DJ background music, which distracts from storytelling and pacing.

## Scope of Work
1. **Service Scaffolding**: Create `services/soundscape` in UV monorepo.
2. **Tension Scoring Engine**: Calculate tension index (0-100) based on active combat state, turn initiative, and character HP levels.
3. **Adaptive Audio Mixer**: Stream dynamic audio stems with automatic ducking during voice agent speech over WebRTC/WebAudio.
4. **Spatial Foley Synthesis**: Trigger environmental soundscapes (rain, cave wind, tavern) linked to tactical board coordinates.

## Acceptance Criteria
1. Music transitions between exploration and combat modes within 1.0s of combat state change.
2. WebAudio client attenuates background audio automatically when voice activity is detected.
3. Action sound effects trigger within 100ms of domain events.
