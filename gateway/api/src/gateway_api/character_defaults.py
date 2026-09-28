"""Default character definitions for initial development and testing."""

from typing import Any

DEFAULT_CHARACTERS: list[dict[str, Any]] = [
    {
        "id": "char-valeros",
        "name": "Valeros of Korvosa",
        "character_class": "Fighter",
        "subclass": "Battle Master",
        "level": 4,
        "current_hp": 38,
        "max_hp": 45,
        "armor_class": 18,
        "speed": 30,
        "campaign_id": "4",
        "owner_id": "user-valeros",
        "portrait_url": "/assets/portraits/fighter.svg",
    },
    {
        "id": "char-kyra",
        "name": "Kyra the Sun Maiden",
        "character_class": "Cleric",
        "subclass": "Life Domain",
        "level": 4,
        "current_hp": 28,
        "max_hp": 32,
        "armor_class": 16,
        "speed": 25,
        "campaign_id": "4",
        "owner_id": "user-kyra",
        "portrait_url": "/assets/portraits/cleric.svg",
    },
    {
        "id": "char-ezren",
        "name": "Ezren the Gray",
        "character_class": "Wizard",
        "subclass": "Evocation",
        "level": 5,
        "current_hp": 22,
        "max_hp": 26,
        "armor_class": 12,
        "speed": 30,
        "campaign_id": None,
        "owner_id": "dev-user-001",
        "portrait_url": "/assets/portraits/wizard.svg",
    },
]
