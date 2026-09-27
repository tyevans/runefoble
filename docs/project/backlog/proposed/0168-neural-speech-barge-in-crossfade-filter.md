---
id: '0168'
title: Neural Speech Barge-In and Soft Crossfade Audio Filter
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

# TASK-0168: Neural Speech Barge-In and Soft Crossfade Audio Filter

## Status
Proposed

## Summary
Implement high-precision voice activity onset detection with 20ms cosine soft crossfading in `services/voice_agent/`, halting AI TTS audio streams within 80ms of human interjection without audible pops or clicks.

## Problem Statement
Abrupt audio clipping during conversational barge-in sounds harsh and unnatural, while delayed cutoffs cause AI speech to clash loudly with human speech for several syllables.

## Governing Architecture & ADRs
- **ADR-0002: Event-Driven Watcher Gameplay Orchestration**: Real-time voice stream lifecycle.
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean DSP audio modules in `voice_agent`.

## Scope of Work
1. **Low-Latency VAD Onset Hook**:
   - Audio ring-buffer evaluator detecting vocalization onset in under 40ms.
2. **Smooth Cosine Crossfade Attenuator**:
   - 20ms soft-fade filter damping outgoing TTS PCM samples gracefully to silence.
3. **Frontdoor Verification**:
   - Synthetic speech benchmark asserting sub-80ms halt time with zero waveform discontinuity artifacts.

## Definition of Done
- Crossfade filter implemented in `services/voice_agent/src/voice_agent/`.
- Unit tests verify total halt latency < 80ms.
- All tests pass via `uv run pytest`.
- File length remains under 200 lines.
