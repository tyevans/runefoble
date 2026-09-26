# Soundscape Microservice

The `soundscape` bounded context is responsible for dynamic background audio stem mixing, tactical foley sound effects, encounter tension scoring, and automatic WebAudio ducking during voice transmission.

## Capabilities

- **Encounter Tension Scoring Engine**: Calculates real-time tension (0–100) based on combat round progression, active enemy CR balance, and lowest party health ratios.
- **Adaptive Audio Stem Mixer**: Crossfades between exploration, tension, combat, and boss musical stems.
- **Ducking Coordinator**: Automatically attenuates background audio by -12dB when player speech or VAD activity is detected.
- **Tactical Foley Sound FX**: Triggers synchronized audio stingers and environmental foley.
- **Microfrontend Controls**: Vendored `<runefoble-soundscape-controls>` Lit Web Component.
