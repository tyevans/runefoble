---
id: '0169'
title: Hardware Acoustic Echo Cancellation and ERLE Validation
status: Proposed
created: 2026-09-26
dependencies:
- TASK-0141
governing_adrs:
- ADR-0002
- ADR-0003
governing_prds:
- PRD-0020
governing_stories:
- US-0060
target_release: 0.7.0
---

# TASK-0169: Hardware Acoustic Echo Cancellation and ERLE Validation

## Status
Proposed

## Summary
Implement adaptive acoustic echo cancellation (AEC) filtering in `services/voice_agent/`, isolating incoming player vocal audio from outgoing room loudspeaker playback to ensure >35dB echo return loss enhancement (ERLE).

## Problem Statement
Tabletop players using desktop speakers rather than headsets frequently experience acoustic feedback loops where AI speech bleeds into the microphone and triggers false intent transcriptions.

## Governing Architecture & ADRs
- **ADR-0002: Event-Driven Watcher Gameplay Orchestration**: Audio stream preprocessing.
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Dedicated DSP filtering modules.

## Scope of Work
1. **Adaptive Least-Mean-Squares (LMS) AEC Filter**:
   - Time-domain adaptive filter subtracting speaker reference signals from microphone capture tracks.
2. **Double-Talk Detector & Cross-Talk Suppressor**:
   - State machine preventing filter divergence during simultaneous human and AI vocalization.
3. **Frontdoor Verification**:
   - Automated benchmark asserting >35dB ERLE across noisy and reverberant test room profiles.

## Definition of Done
- AEC filter module implemented in `services/voice_agent/src/voice_agent/`.
- Echo return loss enhancement verified >35dB in test benchmarks.
- Zero speech-to-intent false triggers observed during speaker playback tests.
- File length remains under 250 lines.
