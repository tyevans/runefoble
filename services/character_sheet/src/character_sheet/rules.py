"""Static game balance rules and progression tables for character sheets."""

SPELL_SLOTS_TABLE: dict[int, dict[int, int]] = {
    1: {1: 2},
    2: {1: 3},
    3: {1: 4, 2: 2},
    4: {1: 4, 2: 3},
    5: {1: 4, 2: 3, 3: 2},
    6: {1: 4, 2: 3, 3: 3},
    7: {1: 4, 2: 3, 3: 3, 4: 1},
    8: {1: 4, 2: 3, 3: 3, 4: 2},
    9: {1: 4, 2: 3, 3: 3, 4: 3, 5: 1},
    10: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2},
}

CLASS_HIT_DIE: dict[str, int] = {
    "barbarian": 12,
    "fighter": 10,
    "paladin": 10,
    "ranger": 10,
    "cleric": 8,
    "druid": 8,
    "monk": 8,
    "rogue": 8,
    "bard": 8,
    "warlock": 8,
    "wizard": 6,
    "sorcerer": 6,
}

KNOWN_SPELL_LEVELS: dict[str, int] = {
    "magic missile": 1,
    "shield": 1,
    "mage armor": 1,
    "cure wounds": 1,
    "guiding bolt": 1,
    "misty step": 2,
    "scorching ray": 2,
    "invisibility": 2,
    "hold person": 2,
    "mirror image": 2,
    "fireball": 3,
    "fly": 3,
    "counterspell": 3,
    "lightning bolt": 3,
    "haste": 3,
}


def get_hit_die_for_class(character_class: str, default: int = 8) -> int:
    """Return the hit die value for a character class, defaulting to d8."""
    return CLASS_HIT_DIE.get(character_class.lower(), default)


def get_spell_slots_for_level(
    level: int, fallback_slots: dict[int, int] | None = None
) -> dict[int, int]:
    """Return the spell slot allocation for a level, defaulting to fallback or level 1 slots."""
    if fallback_slots is None:
        fallback_slots = {1: 2}
    return dict(SPELL_SLOTS_TABLE.get(level, fallback_slots))


def get_known_spell_level(spell_name: str, default: int = 1) -> int:
    """Return the standard spell level for a known spell."""
    return KNOWN_SPELL_LEVELS.get(spell_name.lower(), default)
