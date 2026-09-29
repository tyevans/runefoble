---
id: '0464'
title: Personalized Voice-Cloned Stand-In Dialogue with Dynamic Affliction Slurs
status: Proposed
created: 2026-09-29
dependencies:
- TASK-0006
- TASK-0055
- TASK-0157
governing_adrs:
- ADR-0002
- ADR-0007
governing_prds:
- PRD-0002
- PRD-0004
governing_stories:
- US-0002
- US-0028
target_release: 0.9.0
---

# TASK-0464: Personalized Voice-Cloned Stand-In Dialogue with Dynamic Affliction Slurs

## Status
Proposed

## Summary
Extend `services/voice_agent` to support personalized voice-cloned stand-in dialogue synthesis with real-time acoustic affliction conditioning. Enable players to opt into voice modeling via short audio sample enrollment; when their character acts as an AI stand-in under active DM session miss penalties (e.g., "drunk", "foolishness", "excessive cowardice"), dynamically route synthesized speech through DSP slur transforms (formant pitch wobble, sibilant lengthening, inebriation hiccup cadence) and package the final 2-minute session recap into an exportable MP3 podcast reel stored in Silo S3.

## Problem Statement
PRD-0002 and US-0028 mandate: "Opt-in Voice Model: Players can optionally enroll short voice samples to synthesize their character's dialogue. Dynamic Affliction Slur Conditioning: If the character is afflicted with 'drunk', the synthesized voice automatically applies slurring and formant pitch wobbles. Audio Podcast Delivery: The generated 2-minute session recap with personalized audio commentary is exportable as an MP3 for mobile listening." While generic TTS and basic DSP filters exist in `services/voice_agent/src/voice_agent/dsp.py`, there is no voice-profile reference binding for character stand-ins, no dynamic pipeline coupling active DM absence penalties to speech synthesis modulation in real-time, and no automated export of mobile podcast MP3 bundles.

## Governing Architecture & ADRs
- **ADR-0002: Real-Time Audio Streaming and STT/TTS**: Low-latency voice synthesis and audio streaming pipeline.
- **ADR-0007: Domain-Driven Design Architecture**: Clean domain separation between `voice_agent`, `the_watcher`, and `game_session`.

## Product & User Story References
- [`prd-0002-missing-player-ai-stand-in-with-penalties.md`](../../product/accepted/prd-0002-missing-player-ai-stand-in-with-penalties.md)
- [`us-0002-absent-player-mimicked-by-ai-with-penalties.md`](../../user_stories/accepted/us-0002-absent-player-mimicked-by-ai-with-penalties.md)
- [`us-0028-personalized-voice-cloned-stand-in-dialogue.md`](../../user_stories/accepted/us-0028-personalized-voice-cloned-stand-in-dialogue.md)

## Scope of Work
1. **Stand-In Affliction Acoustic Conditioner (`services/voice_agent/src/voice_agent/standin/affliction_dsp.py`)**:
   - Map active penalties ("drunk", "foolishness", "cowardice") to real-time DSP transforms.
   - For "drunk": apply dynamic pitch modulation, formant frequency shifts, consonant sibilance stretching, and pseudo-random hiccup audio insertions.
   - For "cowardice": apply high-frequency trembling jitter and volume attenuation on assertive syllables.
2. **Opt-in Voice Reference Enrollment (`services/voice_agent/src/voice_agent/standin/voice_profile.py`)**:
   - Store opt-in voice model references linking `user_id` and `character_id` to acoustic embedding parameters.
3. **Session Recap Podcast Exporter (`services/voice_agent/src/voice_agent/standin/podcast_export.py`)**:
   - Assemble a 2-minute MP3 podcast summary weaving stand-in voice commentary with ambient audio stems and scene transition cues.
   - Upload MP3 bundle to Silo S3 with presigned download links.
4. **REST Endpoints (`services/voice_agent/src/voice_agent/routers/standin_voice.py`)**:
   - `POST /api/v1/voice/standin/synthesize`: Synthesize dialogue with character voice model and active penalty modulation.
   - `POST /api/v1/voice/standin/podcast`: Generate and export mobile podcast MP3 reel.
   - `GET /api/v1/voice/standin/podcast/{session_id}/{character_id}`: Query podcast reel status and download URL.

## Definition of Done
1. `affliction_dsp.py`, `voice_profile.py`, and `podcast_export.py` stay strictly < 200 lines each per Hard Invariant 6.
2. Inebriation and cowardice acoustic filters modulate synthesized audio without pipeline stalling.
3. 2-minute MP3 podcast recap generated and persisted to S3 storage.
4. Unit tests confirm DSP parameter calculation and endpoint responses.
