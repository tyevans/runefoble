---
id: '0141'
title: Zero-Latency Neural Voice Duplex & Speech Interruption Handling
status: Proposed
created: 2026-09-26
dependencies:
- TASK-0002
- TASK-0021
- TASK-0039
governing_adrs:
- ADR-0002
target_release: 0.6.0
prd_url: docs/project/product/accepted/prd-0004-dynamic-vocal-audio-conditioning-and-dsp-filters.md
user_story: US-0060
---

# TASK-0141: Zero-Latency Neural Voice Duplex & Speech Interruption Handling

## Status
Proposed

## Summary
Enable natural bidirectional voice interruptions (barge-in) between tabletop players and The Watcher AI Dungeon Master by streaming low-latency VAD speech boundaries, canceling TTS playback within < 100ms, and clearing acoustic echo feedback.

## Problem Statement
When The Watcher narrates atmospheric scenes or lengthy NPC dialogues, players who wish to declare immediate reaction spells (e.g. "I cast Shield!") must currently wait for the entire audio buffer to play out or suffer audio collision. Tabletop conversations require instantaneous speech interruption.

## Governing Architecture & ADRs
- **ADR-0002: Event-Driven Watcher Architecture & Voice Audio**: Sub-100ms audio cancellation and event dispatch over WebSockets.

## Scope of Work
1. **Low-Latency Barge-In Detection (`services/voice_agent/src/voice_agent/barge_in.py`)**:
   - Neural VAD stream analyzer signaling speech interruptions within 80ms.
2. **TTS Audio Stream Cancellation**:
   - Soft 20ms audio crossfade to silence on active playback channels without popping or clipping.
3. **Acoustic Echo Cancellation**:
   - Audio buffer filtering to prevent loudspeaker audio from feeding back into microphone speech transcription.
4. **Frontdoor Blackbox Verification**:
   - Test suite simulating simultaneous playback and player speech interjection.
