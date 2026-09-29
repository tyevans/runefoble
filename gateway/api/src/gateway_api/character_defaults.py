"""Default character definitions for initial development and testing."""

from typing import Any

DEFAULT_RECORD_EQUIPMENT: dict[str, str] = {
    "main_hand": "Longsword +1",
    "off_hand": "Steel Shield",
    "armor": "Chain Mail",
    "accessory": "Ring of Protection",
}

DEFAULT_RECORD_INVENTORY: dict[str, Any] = {
    "i-1": {
        "item_id": "i-1",
        "name": "Longsword +1",
        "quantity": 1,
        "weight_lbs": 3.0,
        "slot": "main_hand",
    },
    "i-2": {
        "item_id": "i-2",
        "name": "Steel Shield",
        "quantity": 1,
        "weight_lbs": 6.0,
        "slot": "off_hand",
    },
    "i-3": {
        "item_id": "i-3",
        "name": "Chain Mail",
        "quantity": 1,
        "weight_lbs": 55.0,
        "slot": "armor",
    },
    "i-4": {
        "item_id": "i-4",
        "name": "Ring of Protection",
        "quantity": 1,
        "weight_lbs": 0.1,
        "slot": "accessory",
    },
    "i-5": {"item_id": "i-5", "name": "Healing Potion", "quantity": 3, "weight_lbs": 0.5},
    "i-6": {"item_id": "i-6", "name": "Rations (5 days)", "quantity": 5, "weight_lbs": 2.0},
}

DEFAULT_RECORD_GUARDRAILS: dict[str, Any] = {
    "preserve_spell_slots": {1: 1},
    "protect_allies": ["Valeros"],
    "protect_ally_hp_threshold": 0.3,
    "risk_threshold": "cautious",
    "avoid_melee": True,
    "permadeath_safeguard": True,
    "custom_priorities": ["Protect allies when low on HP"],
}

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
