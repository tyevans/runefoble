# US-0011: Real-Time Dynamic Voice Filters for Afflicted Characters

## Persona
Sarah (Absent Player) / Marcus (Adventurer)

## User Story
As an adventurer listening to my party members or an absent companion's AI stand-in,
I want the audio synthesis and playback to apply dynamic DSP filters matching their character state (such as slurred drunkenness, echoing whispers, or underwater muffling),
So that our immersion is deepened and the hilarious consequences of missed session penalties come alive audibly.

## Acceptance Criteria
1. When generating speech for a character with the "drunk" condition or penalty, the voice pipeline modulates pitch and alters text with stutter/slur tokens.
2. Filter presets (`drunk`, `whisper`, `underwater`, `ethereal`) alter audio properties deterministically.
3. `/api/v1/voice/tts` accepts a `filters: list[str]` parameter and returns DSP transform metadata alongside synthesized audio.
4. Latency of the DSP filter pipeline is under 50ms.
