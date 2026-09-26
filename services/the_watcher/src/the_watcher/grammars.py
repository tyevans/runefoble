"""Action grammar regular expressions and lexical patterns for The Watcher."""

from __future__ import annotations

import re

# 1. Coordinate movement: e.g. "move to 5, 8", "step to (5, 8)", "go to 5, 8"
COORD_PATTERN: re.Pattern[str] = re.compile(
    r"\b(?:move|step|walk|go|travel|run|dash|advance|retreat)\s+(?:to|towards|at)?\s*\(?\s*(\d+)\s*,\s*(\d+)\s*\)?",
    re.IGNORECASE,
)

# 2a. Cardinal distance movement: e.g. "move 3 squares north", "step 15 feet south"
CARDINAL_DIST_FIRST_PATTERN: re.Pattern[str] = re.compile(
    r"\b(?:move|step|walk|charge|run|advance|retreat|fall back|sprint|dash|head|go)\s+(\d+)\s*(feet|foot|ft|squares?|hexes?|spaces?|steps?|tiles?)?\s*(north|south|east|west|up|down|left|right|northeast|northwest|southeast|southwest|north-east|north-west|south-east|south-west)\b",
    re.IGNORECASE,
)

# 2b. Cardinal distance movement with direction first: e.g. "move north 3 squares", "walk east 10 feet"
CARDINAL_DIR_FIRST_PATTERN: re.Pattern[str] = re.compile(
    r"\b(?:move|step|walk|charge|run|advance|retreat|fall back|sprint|dash|head|go)\s+(north|south|east|west|up|down|left|right|northeast|northwest|southeast|southwest|north-east|north-west|south-east|south-west)\s+(\d+)\s*(feet|foot|ft|squares?|hexes?|spaces?|steps?|tiles?)?\b",
    re.IGNORECASE,
)

# 3. Flanking intent: e.g. "flank the skeleton"
FLANK_PATTERN: re.Pattern[str] = re.compile(
    r"\bflank\s+(?:the\s+)?([a-zA-Z0-9_\-\s]+?)(?:[.!?,]|$)",
    re.IGNORECASE,
)

# 4. Spellcasting: e.g. "cast fireball at 4, 6", "cast magic missile at goblin archer"
SPELL_PATTERN: re.Pattern[str] = re.compile(
    r"\b(?:cast|invoke|channel)\s+([a-zA-Z0-9_\-\s]+?)(?:\s+(?:at|on|towards)\s+(?:the\s+)?([a-zA-Z0-9_\-,\s()]+))?(?:[.!?,]|$)",
    re.IGNORECASE,
)

SPELL_TARGET_COORD_PATTERN: re.Pattern[str] = re.compile(r"\(?\s*(\d+)\s*,\s*(\d+)\s*\)?")

# 5. Move to target token: e.g. "move to the goblin archer", "advance towards the orc"
MOVE_TO_TOKEN_PATTERN: re.Pattern[str] = re.compile(
    r"\b(?:move|step|walk|charge|run|advance|retreat|go)\s+(?:to|towards|next to|near|adjacent to)\s+(?:the\s+)?([a-zA-Z0-9_\-\s]+?)(?:[.!?,]|$)",
    re.IGNORECASE,
)

# 6. Attack: e.g. "attack goblin with longsword", "I slash at the goblin with my sword!", "shoot orc"
ATTACK_PATTERN: re.Pattern[str] = re.compile(
    r"\b(?:attack|strike|hit|shoot|slash|stab|cleave|smite)\s+(?:at\s+)?(?:the\s+)?([a-zA-Z0-9_\-\s]+?)(?:\s+with\s+(?:my\s+|a\s+|an\s+)?([a-zA-Z0-9_\-\s]+))?(?:[.!?,]|$)",
    re.IGNORECASE,
)

GENERIC_ATTACK_PATTERN: re.Pattern[str] = re.compile(
    r"\b(attack|strike|hit|shoot|slash|cleave|smite)\b",
    re.IGNORECASE,
)

# 7. Skill checks: e.g. "stealth check", "make an athletics check", "roll perception"
CANONICAL_SKILLS: tuple[str, ...] = (
    "stealth",
    "perception",
    "athletics",
    "acrobatics",
    "insight",
    "investigation",
    "arcana",
    "history",
    "nature",
    "religion",
    "animal handling",
    "medicine",
    "survival",
    "deception",
    "intimidation",
    "performance",
    "persuasion",
    "initiative",
)
SKILLS_REGEX: str = "|".join(CANONICAL_SKILLS)

SKILL_PATTERN: re.Pattern[str] = re.compile(
    rf"\b(?:make\s+an?|roll\s+an?|roll\s+for\s+)?\s*({SKILLS_REGEX})\s*(?:check)?\b",
    re.IGNORECASE,
)

GENERIC_CHECK_PATTERN: re.Pattern[str] = re.compile(
    r"\b(?:make\s+an?|roll\s+an?|roll\s+for\s+)?\s*([a-zA-Z]+)\s+check\b",
    re.IGNORECASE,
)

# 8. Dice rolls: e.g. "roll 1d20", "roll 2d6+3", "roll a d20"
DICE_PATTERN: re.Pattern[str] = re.compile(
    r"\broll\s+(?:a\s+)?(\d*d\d+(?:[+-]\d+)?)\b",
    re.IGNORECASE,
)
