# PRD-0004: Dynamic Vocal Audio Conditioning and DSP Filters

## Status
Accepted

## Purpose
Voice immersion is paramount in collaborative tabletop roleplaying. When characters are afflicted by magical curses, excessive tavern drinking, fear, or environmental immersion (e.g. underwater, cathedral echo), their audio speech should organically reflect their state without breaking session flow. The `voice_agent` service will provide DSP audio filtering and speech cadence transformation for synthesized AI personas and streamed audio.

## Personas & User Needs
- **Sarah (Absent Player)**: When absent and penalized with "drunk" or "foolishness", her character's AI stand-in speaks with pitch flutters, slight hiccup insertions, and slurred phrasing.
- **Marcus (Adventurer)**: When afflicted by fear or underwater breathing, voice playback applies environmental DSP reverb/muffling.
- **Evelyn (Human DM)**: Auditory cues instantly signal to the whole table what status effects are active on any speaking character.

## Checkable Outcomes
1. The `voice_agent` service provides DSP audio parameter transforms: pitch modulation, cadence warble, low-pass underwater muffling, and cathedral reverb.
2. The `/api/v1/voice/tts` endpoint applies DSP filter pipelines according to active character penalties (`drunk`, `fear`, `ghostly`, `underwater`).
3. Audio chunk metadata indicates active filter presets.
4. Python unit tests verify filter pipeline output and parameter scaling.
