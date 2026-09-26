"""Autonomous DM Scene Presets and Atmosphere Generation.

Maintains catalogs of narrative environment presets and constructs
dynamic scene atmosphere events.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from runefoble_events.events import SceneAtmosphereSet

SCENE_PRESETS: dict[str, dict[str, Any]] = {
    "dungeon": {
        "name": "Forgotten Underhalls",
        "lighting": "dim flickering torches casting elongated shadows",
        "descriptions": {
            "suspenseful": (
                "Damp stonework glistens under dying torchlight. The distant, rhythmic drip of"
                " water echoes like a ticking clock."
            ),
            "eerie": (
                "Chill air drafts up from cracks in flagstones. Pale luminescent mold clings"
                " to walls, whispering faintly."
            ),
            "foreboding": (
                "Scratch marks gouge deep into stone walls. Ancient iron portcullises hang"
                " bent and battered aside."
            ),
        },
        "ambient_audio": (
            "subterranean dungeon ambiance, distant water dripping, faint low hum, damp echoing"
            " cavern"
        ),
    },
    "crypt": {
        "name": "Crypt of the Restless Kings",
        "lighting": "pale cold luminescence from weeping wall moss",
        "descriptions": {
            "suspenseful": (
                "Ancient stone sarcophagi line the walls. A bone-chilling draft stirs dry"
                " funerary shrouds."
            ),
            "eerie": (
                "Muffled whispers drift from sealed burial niches. Scent of embalming myrrh"
                " fills every breath with bitter cold."
            ),
            "foreboding": (
                "Shattered seals on the royal tomb signify a broken ward. Shadows congregate"
                " unnaturally around the dais."
            ),
        },
        "ambient_audio": (
            "eerie crypt silence, faint mournful wind, scratching behind stone tombs, low"
            " choir drone"
        ),
    },
    "tavern": {
        "name": "The Wayward Drake Inn",
        "lighting": "warm hearth glow interspersed with flickering tallow candles",
        "descriptions": {
            "suspenseful": (
                "Heavy oak beams creak overhead as roasted meat scents mingle with uneasy"
                " murmurs among cloaked patrons."
            ),
            "eerie": (
                "The tavern patrons stare blankly into untouched ale. Even the roaring fire"
                " produces no comforting warmth."
            ),
            "cozy": (
                "A roaring hearth crackles merrily. The bard strums a lively ballad as"
                " tankards clatter in hearty toasts."
            ),
        },
        "ambient_audio": (
            "busy medieval tavern background noise, clinking flagons, muffled hearth fire crackle"
        ),
    },
    "forest": {
        "name": "Whispering Pines of Eldermoor",
        "lighting": "dappled moonlight piercing through gnarled pine canopy",
        "descriptions": {
            "suspenseful": (
                "Thick silver fog coils around roots. Nocturnal creatures fall dead silent as"
                " unnatural frost creeps."
            ),
            "eerie": (
                "Twisted branches form gaunt silhouettes against twilight. Faint spirit"
                " lights dance between briars."
            ),
            "foreboding": (
                "Giant claw ruts tear through mossy bark. Scent of ozone and predator musk"
                " signals a prowling apex beast."
            ),
        },
        "ambient_audio": (
            "deep forest night wind, rustling pine needles, distant hoot of an owl, ominous"
            " creaking branches"
        ),
    },
    "dragon_lair": {
        "name": "Scorched Crag of the Wyrm",
        "lighting": "smoldering magma fissures casting an intense crimson gleam",
        "descriptions": {
            "suspenseful": (
                "Charred dragon scales crunch underfoot. The acrid stench of sulfur hangs"
                " thick with cavernous exhalations."
            ),
            "eerie": (
                "Gleaming treasures are fused into glassy obsidian walls. The heat is"
                " suffocating, yet icy dread grips the heart."
            ),
            "deadly": (
                "Molten rivers pulse with violent fury. Towering stalactites tremble as"
                " massive wings unfurl above."
            ),
        },
        "ambient_audio": (
            "volcanic cave rumble, magma bubbling, distant low reptile breathing, crackling"
            " ember heat"
        ),
    },
}


def build_scene_atmosphere(
    session_id: str,
    location_type: str = "dungeon",
    mood: str = "suspenseful",
) -> SceneAtmosphereSet:
    """Set dynamic scene atmosphere, location details, lighting, and ambient audio prompt."""
    loc_key = location_type.lower().strip().replace(" ", "_")
    mood_key = mood.lower().strip()

    preset = SCENE_PRESETS.get(loc_key)
    if preset:
        location_name = preset["name"]
        lighting = preset["lighting"]
        descriptions = preset["descriptions"]
        description = descriptions.get(mood_key) or next(iter(descriptions.values()))
        ambient_prompt = preset["ambient_audio"]
    else:
        clean_name = location_type.replace("_", " ").title()
        location_name = f"{clean_name} Environs"
        lighting = f"moody illumination highlighting the {mood_key} atmosphere"
        description = (
            f"The party stands within the {clean_name}. A palpable {mood_key} tension"
            " pervades every shadow."
        )
        ambient_prompt = (
            f"atmospheric fantasy soundscape, {clean_name} ambience, {mood_key} tension"
        )

    return SceneAtmosphereSet(
        session_id=session_id,
        scene_id=f"scene-{uuid4().hex[:8]}",
        location_name=location_name,
        lighting=lighting,
        mood=mood,
        description=description,
        ambient_audio_prompt=ambient_prompt,
    )
