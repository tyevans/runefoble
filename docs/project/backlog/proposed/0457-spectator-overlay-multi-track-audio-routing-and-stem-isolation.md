---
id: '0457'
title: Spectator Overlay Multi-Track Audio Routing and Stem Isolation
status: Proposed
created: 2026-09-29
dependencies:
- TASK-0050
- TASK-0056
- TASK-0436
governing_adrs:
- ADR-0002
- ADR-0004
- ADR-0010
governing_prds:
- PRD-0010
- PRD-0011
governing_stories:
- US-0030
target_release: 0.9.0
---

# TASK-0457: Spectator Overlay Multi-Track Audio Routing and Stem Isolation

## Status
Proposed

## Summary
Implement multi-track WebAudio destination routing and discrete audio stem isolation for the OBS spectator stream overlay (`<runefoble-stream-overlay>`). Route Watcher DM speech synthesis, player character WebRTC voice streams, background ambient music stems, and tactical foley audio into separate WebAudio sub-buses and URL-configurable browser-source audio channels, allowing OBS Studio to record and balance each audio stem independently on discrete mixer tracks.

## Problem Statement
Broadcasting live tabletop RPGs in OBS requires professional audio balancing. Currently, audio playback mixes all voices, ambient music, and sound effects into a single stereo output (PRD-0011, US-0030). If a character speaks during intense combat music, stream viewers may struggle to hear the dialogue, and the streamer has no way in OBS to adjust the volume of the DM voice without also changing the music volume or game sound effects.

## Governing Architecture & ADRs
- **ADR-0002: Real-time Audio Architecture**: Low-latency audio processing and WebAudio nodes.
- **ADR-0004: Lit Web Components and Storybook UI**: Stream overlay component configuration.
- **ADR-0010: Continuous Integration Pipeline**: Frontdoor blackbox test validation.

## Product & User Story References
- [`prd-0010-adaptive-soundscape-foley-and-tension-scoring.md`](../../product/accepted/prd-0010-adaptive-soundscape-foley-and-tension-scoring.md)
- [`prd-0011-live-spectator-studio-and-audience-interactivity.md`](../../product/accepted/prd-0011-live-spectator-studio-and-audience-interactivity.md)
- [`us-0030-obs-transparent-party-vitals-and-multi-track-audio.md`](../../user_stories/accepted/us-0030-obs-transparent-party-vitals-and-multi-track-audio.md)

## Scope of Work
1. **Multi-Track WebAudio Bus (`frontend/src/services/multi-track-audio-bus.ts`)**:
   - Create an AudioContext with 4 distinct sub-buses:
     - Track 1: Watcher AI DM Narration
     - Track 2: Player Character Speech (WebRTC peer streams)
     - Track 3: Dynamic Soundscape Music Stems (ambient, tension, combat)
     - Track 4: Kinetic Foley & Dice Roll SFX
   - Connect each sub-bus to discrete gain nodes with individual mute/solo controls.
2. **OBS URL Audio Track Filter Parameters**:
   - Support query parameters on the spectator route (`#/spectator?track=dm_voice`, `?track=music`, `?track=all`):
     - Allows streamers to embed multiple instances of the OBS browser source with dedicated audio outputs mapped to separate OBS mixer tracks.
3. **Blackbox Integration Tests (`tests/test_blackbox_spectator_multi_track_audio.py`)**:
   - Verify AudioContext initialization and node graph wiring under each query param configuration.
   - Assert stem isolation and -12dB voice ducking attenuation on the music track when DM or player speaks.

## Definition of Done
1. `frontend/src/services/multi-track-audio-bus.ts` implemented strictly < 250 lines.
2. Spectator overlay respects `?track=` parameters and isolates requested audio sub-buses.
3. Blackbox test suite passes with 100% assertions.
4. Code passes lint and type checks.
