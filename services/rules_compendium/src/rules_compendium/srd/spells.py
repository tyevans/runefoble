"""Canonical SRD 5.1 spells dataset."""

from typing import Any

CANONICAL_SPELLS: list[dict[str, Any]] = [
    {
        "name": "Fireball",
        "level": 3,
        "school": "Evocation",
        "casting_time": "1 action",
        "range": "150 feet",
        "components": "V, S, M (a tiny ball of bat guano and sulfur)",
        "duration": "Instantaneous",
        "description": (
            "A bright streak flashes from your pointing finger to a point you choose within range "
            "and blossoms into an explosion of flame. Each creature in a 20-foot-radius sphere "
            "must make a Dexterity saving throw. A target takes 8d6 fire damage on a failed save, "
            "or half as much on a successful one."
        ),
    },
    {
        "name": "Cure Wounds",
        "level": 1,
        "school": "Evocation",
        "casting_time": "1 action",
        "range": "Touch",
        "components": "V, S",
        "duration": "Instantaneous",
        "description": (
            "A creature you touch regains a number of hit points equal to 1d8 + your spellcasting "
            "ability modifier. This spell has no effect on undead or constructs."
        ),
    },
    {
        "name": "Hold Person",
        "level": 2,
        "school": "Enchantment",
        "casting_time": "1 action",
        "range": "60 feet",
        "components": "V, S, M (a small, straight piece of iron)",
        "duration": "Concentration, up to 1 minute",
        "description": (
            "Choose a humanoid that you can see within range. The target must succeed on a Wisdom "
            "saving throw or be paralyzed for the duration. At the end of each of its turns, "
            "the target can make another Wisdom saving throw."
        ),
    },
    {
        "name": "Magic Missile",
        "level": 1,
        "school": "Evocation",
        "casting_time": "1 action",
        "range": "120 feet",
        "components": "V, S",
        "duration": "Instantaneous",
        "description": (
            "You create three glowing darts of magical force. Each dart hits a creature of your choice "
            "that you can see within range, dealing 1d4 + 1 force damage to its target. The darts all "
            "strike simultaneously and you can direct them to hit one creature or several."
        ),
    },
    {
        "name": "Shield",
        "level": 1,
        "school": "Abjuration",
        "casting_time": "1 reaction (which you take when hit by an attack or targeted by magic missile)",
        "range": "Self",
        "components": "V, S",
        "duration": "1 round",
        "description": (
            "An invisible barrier of magical force appears and protects you. Until the start of your "
            "next turn, you have a +5 bonus to AC, including against the triggering attack, and you take "
            "no damage from magic missile."
        ),
    },
    {
        "name": "Blindness/Deafness",
        "level": 2,
        "school": "Necromancy",
        "casting_time": "1 action",
        "range": "30 feet",
        "components": "V",
        "duration": "1 minute",
        "description": (
            "You can blind or deafen a foe. Choose one creature that you can see within range to make "
            "a Constitution saving throw. If it fails, the target is either blinded or deafened (your choice) "
            "for the duration. At the end of each of its turns, the target can make another Constitution saving throw."
        ),
    },
    {
        "name": "Misty Step",
        "level": 2,
        "school": "Conjuration",
        "casting_time": "1 bonus action",
        "range": "Self",
        "components": "V",
        "duration": "Instantaneous",
        "description": (
            "Briefly surrounded by silvery mist, you teleport up to 30 feet to an unoccupied space "
            "that you can see."
        ),
    },
    {
        "name": "Healing Word",
        "level": 1,
        "school": "Evocation",
        "casting_time": "1 bonus action",
        "range": "60 feet",
        "components": "V",
        "duration": "Instantaneous",
        "description": (
            "A creature of your choice that you can see within range regains hit points equal to "
            "1d4 + your spellcasting ability modifier."
        ),
    },
]
