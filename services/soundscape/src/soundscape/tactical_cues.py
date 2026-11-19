"""Map tactical board events to foley cue parameters (TASK-0438).

Each function returns the resolved cue for one board event. The handlers record the cue on the
session aggregate, which publishes SoundscapeCueTriggered.
"""

from __future__ import annotations

import re
from typing import Any

from soundscape.mixer import AudioStemMixer

# Impact energy at which an impact cue plays at full gain (board physics units).
IMPACT_REFERENCE_ENERGY = 50.0
MIN_IMPACT_GAIN = 0.2
MAX_IMPACT_GAIN = 1.5

_NON_SLUG = re.compile(r"[^a-z0-9]+")


def _slug(name: str) -> str:
    """Turn a free-text board label into a lowercase asset name, such as 'spike pit' to 'spike_pit'."""
    return _NON_SLUG.sub("_", name.lower()).strip("_") or "generic"


def hazard_cue(hazard_type: str) -> dict[str, Any]:
    """Return the sound effect for a token that trips an environmental hazard."""
    return AudioStemMixer().resolve_foley_cue(
        cue_name=f"hazard_{_slug(hazard_type)}", cue_type="sfx"
    )


def impact_cue(collision_type: str, impact_energy: float) -> dict[str, Any]:
    """Return the impact sound for a physical collision. Louder impacts carry more energy."""
    gain = min(MAX_IMPACT_GAIN, max(MIN_IMPACT_GAIN, impact_energy / IMPACT_REFERENCE_ENERGY))
    return AudioStemMixer().resolve_foley_cue(
        cue_name=f"impact_{_slug(collision_type)}", cue_type="sfx", volume_gain=gain
    )
