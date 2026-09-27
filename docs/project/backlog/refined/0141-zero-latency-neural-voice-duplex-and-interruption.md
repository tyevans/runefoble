---
id: '0141'
title: Zero-Latency Neural Voice Duplex & Speech Interruption Handling
status: Refined
created: 2026-09-26
dependencies:
- TASK-0002
- TASK-0021
- TASK-0033
- TASK-0039
governing_adrs:
- ADR-0002
- ADR-0006
governing_prds:
- PRD-0004
governing_stories:
- US-0060
target_release: 0.6.0
---

# TASK-0141: Zero-Latency Neural Voice Duplex & Speech Interruption Handling

## Status
Refined

## Summary
Enable natural bidirectional voice interruptions (barge-in) between tabletop players and The Watcher AI Dungeon Master by streaming low-latency VAD speech boundaries, canceling TTS playback within < 100ms, and clearing acoustic echo feedback.

## Problem Statement
When The Watcher narrates atmospheric scenes or lengthy NPC dialogues, players who wish to declare immediate reaction spells (e.g. "I cast Shield!") must currently wait for the entire audio buffer to play out or suffer audio collision. Tabletop conversations require instantaneous speech interruption without robotic delays or clipped audio artifacts.

## Governing Architecture & ADRs
- **ADR-0002: Event-Driven Watcher Architecture & Voice Audio**: Sub-100ms audio cancellation and event dispatch over WebSockets and Redis Streams.
- **ADR-0006: Redis Streams Event Bus Architecture**: Broadcasting `voice.speech.interrupted` domain events to pause narration aggregates.

## Product & User Story References
- **Product Requirement**: [`prd-0004-dynamic-vocal-audio-conditioning-and-dsp-filters.md`](../../product/accepted/prd-0004-dynamic-vocal-audio-conditioning-and-dsp-filters.md)
- **User Story**: [`us-0060-zero-latency-neural-voice-duplex.md`](../../user_stories/accepted/us-0060-zero-latency-neural-voice-duplex.md)

## Detailed Specification & Implementation Plan
1. **Low-Latency Barge-In Detection (`services/voice_agent/src/voice_agent/barge_in.py`)**:
   - Neural VAD stream analyzer signaling speech interruptions within 80ms of human speech onset (< 150 lines).
2. **TTS Audio Stream Cancellation (`services/voice_agent/src/voice_agent/interruption.py`)**:
   - Soft 20ms audio crossfade to silence on active playback channels without popping or clipping, triggering cancellation tokens (< 140 lines).
3. **Acoustic Echo Cancellation Filter (`services/voice_agent/src/voice_agent/echo_canceller.py`)**:
   - Adaptive filter suppressing speaker output from microphone input buffers, avoiding false-positive barge-in triggers (< 130 lines).
4. **WebSocket Voice Duplex Signaling (`services/voice_agent/src/voice_agent/routers/duplex.py`)**:
   - WebSocket control frames notifying clients and The Watcher of barge-in state transitions (< 140 lines).
5. **Domain Event Publication**:
   - Emit `voice.speech.interrupted` over Redis Streams so The Watcher immediately saves conversational state and listens to player interjection.

## INVEST Criteria Evaluation
- **Independent (I)**: Independent voice agent capability integrated via standard WebSocket and Redis Streams interfaces.
- **Negotiable (N)**: VAD sensitivity threshold and crossfade curve can be tuned.
- **Valuable (V)**: Transforms AI DM interaction into fluid, human-feeling conversational turn-taking.
- **Estimable (E)**: Builds upon existing WebRTC signaling (TASK-0033) and streaming Whisper (TASK-0039).
- **Small (S)**: Bounded strictly to `services/voice_agent/`; all files < 160 lines.
- **Testable (T)**: Frontdoor blackbox tests simulating concurrent TTS playback and player voice injection.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Pipeline Implementation**:
   - `barge_in.py`, `interruption.py`, `echo_canceller.py`, and `routers/duplex.py` implemented.
   - All files strictly < 180 lines.
2. **Frontdoor Blackbox Verification**:
   - `tests/test_blackbox_voice_duplex.py` verifying:
     - Audio playback canceled within 100ms of simulated speech.
     - `voice.speech.interrupted` event emitted with timestamp and remaining narration text.
     - WebRTC signaling confirms audio stream mute/cancellation.
3. **Quality Gates**:
   - `uv run pytest tests/test_blackbox_voice_duplex.py` passes cleanly.
   - Passes `uv run ruff check .` and `uv run ruff format --check .`.
