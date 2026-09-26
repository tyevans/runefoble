"""Adaptive audio stem mixer & WebAudio ducking coordinator (TASK-0050).

Manages multi-track stem layers (ambient, tension, combat, boss) with smooth
interpolation matrices, tactical sound foley catalog, and -12dB WebAudio ducking.
"""

from __future__ import annotations

import math
from typing import Any

# Standard ducking attenuation: -12 dB corresponds to 10^(-12/20) ~ 0.2512 linear gain
DUCKING_ATTENUATION_DB = -12.0
DUCKING_LINEAR_MULTIPLIER = math.pow(10.0, DUCKING_ATTENUATION_DB / 20.0)

# Default stem profiles with crossfade gain distributions
STEM_PROFILE_WEIGHTS: dict[str, dict[str, float]] = {
    "exploration": {
        "ambient": 1.0,
        "tension": 0.0,
        "combat": 0.0,
        "boss": 0.0,
    },
    "tension": {
        "ambient": 0.4,
        "tension": 0.9,
        "combat": 0.2,
        "boss": 0.0,
    },
    "combat": {
        "ambient": 0.1,
        "tension": 0.3,
        "combat": 1.0,
        "boss": 0.2,
    },
    "boss": {
        "ambient": 0.0,
        "tension": 0.2,
        "combat": 0.6,
        "boss": 1.0,
    },
}

# Catalog of tactical foley and acoustic stingers
TACTICAL_FOLEY_CATALOG: dict[str, dict[str, Any]] = {
    "fireball": {
        "sound_url": "http://silo:9000/runefoble-assets/audio/foley/fireball.ogg",
        "cue_type": "spell",
        "volume_gain": 1.0,
        "duck_music": True,
    },
    "sword_slash": {
        "sound_url": "http://silo:9000/runefoble-assets/audio/foley/sword_slash.ogg",
        "cue_type": "melee",
        "volume_gain": 1.0,
        "duck_music": False,
    },
    "shield_block": {
        "sound_url": "http://silo:9000/runefoble-assets/audio/foley/shield_block.ogg",
        "cue_type": "melee",
        "volume_gain": 0.9,
        "duck_music": False,
    },
    "critical_hit": {
        "sound_url": "http://silo:9000/runefoble-assets/audio/foley/critical_hit.ogg",
        "cue_type": "stinger",
        "volume_gain": 1.2,
        "duck_music": True,
    },
    "dungeon_drip": {
        "sound_url": "http://silo:9000/runefoble-assets/audio/foley/dungeon_drip.ogg",
        "cue_type": "ambient",
        "volume_gain": 0.7,
        "duck_music": False,
    },
    "thunder_clap": {
        "sound_url": "http://silo:9000/runefoble-assets/audio/foley/thunder_clap.ogg",
        "cue_type": "foley",
        "volume_gain": 1.1,
        "duck_music": True,
    },
}


class AudioStemMixer:
    """Manages audio stem gains, ducking attenuation, and foley presets."""

    def __init__(
        self,
        stem_profile: str = "exploration",
        master_volume: float = 1.0,
    ) -> None:
        self.stem_profile = stem_profile
        self.master_volume = master_volume
        self.is_ducked = False
        self.ducking_reason: str = "none"

    def get_stem_weights(self, profile: str | None = None) -> dict[str, float]:
        """Return raw stem weight matrix for given or current profile."""
        target_profile = profile or self.stem_profile
        return STEM_PROFILE_WEIGHTS.get(target_profile, STEM_PROFILE_WEIGHTS["exploration"]).copy()

    def get_effective_gain(self) -> float:
        """Calculate effective master gain considering voice ducking."""
        base = self.master_volume
        if self.is_ducked:
            return round(base * DUCKING_LINEAR_MULTIPLIER, 4)
        return round(base, 4)

    def calculate_active_stem_gains(self) -> dict[str, float]:
        """Compute final output volume for each stem incorporating master & ducking gain."""
        weights = self.get_stem_weights()
        effective_gain = self.get_effective_gain()
        return {stem: round(weight * effective_gain, 4) for stem, weight in weights.items()}

    def set_ducking(self, ducked: bool, reason: str = "speech") -> None:
        """Toggle ducking state (-12dB attenuation on active voice)."""
        self.is_ducked = ducked
        self.ducking_reason = reason if ducked else "none"

    def resolve_foley_cue(
        self,
        cue_name: str | None,
        sound_url: str | None = None,
        cue_type: str = "foley",
        volume_gain: float = 1.0,
        duck_music: bool = False,
    ) -> dict[str, Any]:
        """Resolve a tactical cue from catalog presets or custom inputs."""
        if cue_name and cue_name in TACTICAL_FOLEY_CATALOG:
            preset = TACTICAL_FOLEY_CATALOG[cue_name]
            return {
                "cue_name": cue_name,
                "sound_url": sound_url or preset["sound_url"],
                "cue_type": preset["cue_type"],
                "volume_gain": volume_gain if volume_gain != 1.0 else preset["volume_gain"],
                "duck_music": duck_music or preset["duck_music"],
            }

        resolved_url = (
            sound_url
            or f"http://silo:9000/runefoble-assets/audio/foley/{cue_name or 'generic_cue'}.ogg"
        )
        return {
            "cue_name": cue_name,
            "sound_url": resolved_url,
            "cue_type": cue_type,
            "volume_gain": volume_gain,
            "duck_music": duck_music,
        }
