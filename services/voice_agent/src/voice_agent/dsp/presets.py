"""NPC Vocal Preset Profiles for Tabletop Voice Modulation."""

from __future__ import annotations

from pydantic import BaseModel, Field


class NPCVoicePreset(BaseModel):
    """Vocal DSP profile for creature and NPC archetypes."""

    preset_id: str
    name: str
    description: str
    pitch_shift_semitones: float = 0.0
    formant_shift: float = 1.0
    resonance_hz: float = 0.0
    octave_offset: float = 0.0
    reverb_wet: float = 0.0
    ring_mod_hz: float = 0.0
    gain_db: float = 0.0
    active_filters: list[str] = Field(default_factory=list)


ANCIENT_DRAGON = NPCVoicePreset(
    preset_id="ancient-dragon",
    name="Ancient Dragon",
    description="Sub-bass chest resonance and lowered pitch for colossal draconic presence.",
    pitch_shift_semitones=-7.0,
    formant_shift=0.75,
    resonance_hz=140.0,
    octave_offset=-0.5,
    reverb_wet=0.35,
    gain_db=4.0,
    active_filters=["dragon_growl", "sub_bass_resonance"],
)

GOBLIN_SKULKER = NPCVoicePreset(
    preset_id="goblin-skulker",
    name="Goblin Skulker",
    description="High-pitched shrieks and contracted formants for frantic subterranean creatures.",
    pitch_shift_semitones=6.5,
    formant_shift=1.4,
    resonance_hz=2800.0,
    octave_offset=0.5,
    reverb_wet=0.1,
    gain_db=2.0,
    active_filters=["screeching_goblin", "nasal_shimmer"],
)

CELESTIAL_SPIRIT = NPCVoicePreset(
    preset_id="celestial-spirit",
    name="Celestial Spirit",
    description="Ethereal shimmer with resonant high formants and reverberant vocal wash.",
    pitch_shift_semitones=3.0,
    formant_shift=1.2,
    resonance_hz=1600.0,
    octave_offset=0.25,
    reverb_wet=0.65,
    gain_db=1.0,
    active_filters=["ethereal_echo", "celestial_harmonics"],
)

ROBOTIC_CONSTRUCT = NPCVoicePreset(
    preset_id="robotic-construct",
    name="Robotic Construct",
    description="Metallic ring modulation and digitized comb filtering for automatons.",
    pitch_shift_semitones=-2.0,
    formant_shift=0.95,
    resonance_hz=440.0,
    octave_offset=0.0,
    ring_mod_hz=60.0,
    reverb_wet=0.15,
    gain_db=1.5,
    active_filters=["robotic_construct", "ring_modulation"],
)

PRESETS_BY_ID: dict[str, NPCVoicePreset] = {
    p.preset_id: p for p in (ANCIENT_DRAGON, GOBLIN_SKULKER, CELESTIAL_SPIRIT, ROBOTIC_CONSTRUCT)
}

PRESETS_BY_NAME: dict[str, NPCVoicePreset] = {
    p.name.lower(): p for p in (ANCIENT_DRAGON, GOBLIN_SKULKER, CELESTIAL_SPIRIT, ROBOTIC_CONSTRUCT)
}


def get_preset(identifier: str | None) -> NPCVoicePreset | None:
    """Lookup NPC vocal preset by ID or name (case-insensitive)."""
    if not identifier:
        return None
    norm = identifier.strip().lower().replace("_", "-").replace(" ", "-")
    direct = PRESETS_BY_ID.get(norm)
    if direct:
        return direct
    return PRESETS_BY_NAME.get(identifier.strip().lower())


def list_presets() -> list[NPCVoicePreset]:
    """Return all available NPC vocal presets."""
    return list(PRESETS_BY_ID.values())


__all__ = [
    "ANCIENT_DRAGON",
    "CELESTIAL_SPIRIT",
    "GOBLIN_SKULKER",
    "NPCVoicePreset",
    "PRESETS_BY_ID",
    "PRESETS_BY_NAME",
    "ROBOTIC_CONSTRUCT",
    "get_preset",
    "list_presets",
]
