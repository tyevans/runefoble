---
id: '0482'
title: WebAudio Client-Side Formant and Pitch Shifting DSP Node Chain
status: Proposed
created: 2026-09-29
dependencies:
- TASK-0033
- TASK-0068
governing_adrs:
- ADR-0002
- ADR-0004
governing_prds:
- PRD-0004
governing_stories:
- US-0011
- US-0020
target_release: 0.9.0
---

# TASK-0482: WebAudio Client-Side Formant and Pitch Shifting DSP Node Chain

## Status
Proposed

## Summary
Extend `WebAudioPipeline` (`frontend/src/services/webaudio-pipeline.ts`) to implement client-side WebAudio DSP node chains for real-time NPC formant warping and pitch modulation (supporting "Ancient Dragon", "Goblin Skulker", "Celestial Spirit", and "Robotic Construct" presets), enabling zero-latency local DM vocal preview and microphone transformation before WebRTC peer transmission.

## Problem Statement
In `frontend/src/services/webaudio-pipeline.ts`, `WebAudioPipeline.applyDspFilters()` currently supports only basic biquad filters for character condition effects (`underwater`, `whisper`, `ethereal`, `drunk`). There is no client-side node graph for NPC voice modulation presets. Consequently, when Evelyn speaks as an NPC, the audio either requires server-side transcoding latency or cannot be auditioned locally in real-time. To maintain the sub-500ms pipeline budget (and <50ms processing SLA), client-side WebAudio audio nodes must directly condition outgoing microphone tracks.

## Governing Architecture & ADRs
- **ADR-0002: Real-time Audio Architecture**: Sub-500ms voice pipeline with local WebAudio pre-processing before WebRTC peer distribution.
- **ADR-0004: Lit Web Components and Storybook UI**: Exposing audio preview and parameter configuration within microfrontends.

## Product & User Story References
- [`prd-0004-dynamic-vocal-audio-conditioning-and-dsp-filters.md`](../../product/accepted/prd-0004-dynamic-vocal-audio-conditioning-and-dsp-filters.md)
- [`us-0011-dynamic-voice-filters-for-afflicted-characters.md`](../../user_stories/accepted/us-0011-dynamic-voice-filters-for-afflicted-characters.md)
- [`us-0020-dm-vocal-modulator-with-realtime-npc-filtering.md`](../../user_stories/accepted/us-0020-dm-vocal-modulator-with-realtime-npc-filtering.md)

## Scope of Work
1. **NPC Preset DSP Node Architecture (`frontend/src/services/webaudio-pipeline.ts`)**:
   - Add `applyPreset(presetName: string, options?: PresetOptions): void` to `WebAudioPipeline`.
   - Implement DSP node graph for **Ancient Dragon**: Cascaded low-pass BiquadFilter (sub-bass boost at 80Hz), pitch down-transposition simulation via delay modulation, and slight saturation.
   - Implement DSP node graph for **Goblin Skulker**: High-pass resonance at 1.8kHz, formant peak booster, and rapid flutter tremolo.
   - Implement DSP node graph for **Celestial Spirit**: Multi-tap stereo delay lines (300ms, 450ms) with high-resonance shimmer feedback.
   - Implement DSP node graph for **Robotic Construct**: Ring modulator / WaveShaperNode frequency comb filter with 50Hz carrier.
2. **Local Audio Preview / Audition Mode**:
   - Provide a loopback audition toggle in `WebAudioPipeline` (`enableAudition(enabled: boolean)`), routing filtered audio to local headphones without echoing to remote peers.
3. **WebRTC Track Integration (`frontend/src/services/webrtc-voice.ts`)**:
   - Ensure the processed MediaStream destination node track is cleanly forwarded to `PeerConnectionMesh` local tracks when presets change dynamically during a live call.
4. **Unit and Storybook Tests**:
   - Author tests in `frontend/test/webaudio-pipeline.test.ts` verifying graph reconstruction, node connections, and parameter boundary validation.

## Definition of Done
1. `WebAudioPipeline.applyPreset()` configures distinct, audible audio node graphs for all 4 canonical presets.
2. Processing overhead remains imperceptible (< 15ms WebAudio graph traversal latency).
3. Switching presets during an active microphone capture does not glitch or disconnect WebRTC peer connections.
4. Audition mode allows DMs to hear their modulated voice locally before speaking live.
5. All source files conform strictly to Hard Invariant 6 (< 500 lines).
