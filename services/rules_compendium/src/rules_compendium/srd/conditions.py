"""Canonical SRD 5.1 conditions dataset."""

from typing import Any

CANONICAL_CONDITIONS: list[dict[str, Any]] = [
    {
        "name": "Blinded",
        "description": "A blinded creature can't see and automatically fails any ability check that requires sight.",
        "effects": [
            "Automatically fails any ability check that requires sight.",
            "Attack rolls against the creature have advantage.",
            "The creature's attack rolls have disadvantage.",
        ],
    },
    {
        "name": "Charmed",
        "description": "A charmed creature can't attack the charmer or target them with harmful abilities or magical effects.",
        "effects": [
            "Can't attack the charmer or target them with harmful abilities.",
            "The charmer has advantage on any ability check to interact socially with the creature.",
        ],
    },
    {
        "name": "Paralyzed",
        "description": "A paralyzed creature is incapacitated and can't move or speak.",
        "effects": [
            "Incapacitated and cannot move or speak.",
            "Automatically fails Strength and Dexterity saving throws.",
            "Attack rolls against the creature have advantage.",
            "Any attack that hits the creature is a critical hit if the attacker is within 5 feet.",
        ],
    },
    {
        "name": "Prone",
        "description": "A prone creature's only movement option is to crawl, unless it stands up.",
        "effects": [
            "Only movement option is to crawl, unless it stands up (costing half its movement).",
            "The creature has disadvantage on attack rolls.",
            "An attack roll against the creature has advantage if the attacker is within 5 feet; otherwise disadvantage.",
        ],
    },
    {
        "name": "Stunned",
        "description": "A stunned creature is incapacitated, can't move, and can speak only falteringly.",
        "effects": [
            "Incapacitated, cannot move, and speaks only falteringly.",
            "Automatically fails Strength and Dexterity saving throws.",
            "Attack rolls against the creature have advantage.",
        ],
    },
    {
        "name": "Frightened",
        "description": "A frightened creature has disadvantage on ability checks and attack rolls while the source of its fear is within sight.",
        "effects": [
            "Disadvantage on ability checks and attack rolls while the source of fear is in line of sight.",
            "Cannot willingly move closer to the source of its fear.",
        ],
    },
    {
        "name": "Incapacitated",
        "description": "An incapacitated creature cannot take actions or reactions.",
        "effects": [
            "Cannot take actions or reactions.",
        ],
    },
    {
        "name": "Invisible",
        "description": "An invisible creature is impossible to see without the aid of magic or a special sense.",
        "effects": [
            "Heavily obscured for the purpose of hiding.",
            "Attack rolls against the creature have disadvantage.",
            "The creature's attack rolls have advantage.",
        ],
    },
]
