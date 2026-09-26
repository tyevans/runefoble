"""RPG constants, spell descriptions, and condition rule effects for MCP tools."""

SPELL_EFFECTS: dict[str, str] = {
    "fireball": "Deals 8d6 fire damage in a 20-foot radius sphere. Dexterity saving throw (DC 15) for half.",
    "cure wounds": "Heals target for {level}d8 + 3 hit points on physical touch.",
    "magic missile": "Fires {darts} unerring darts of magical force dealing 1d4+1 force damage each.",
    "shield": "Adds +5 to AC until the start of your next turn and nullifies Magic Missile.",
    "healing word": "Heals target for {level}d4 + 3 as a bonus action up to 60 feet.",
}

CONDITION_RULES: dict[str, str] = {
    "blinded": "Automatically fails ability checks requiring sight. Attack rolls against have advantage, attacks have disadvantage.",
    "prone": "Movement costs extra. Attack rolls made with disadvantage. Melee attacks against have advantage.",
    "frightened": "Disadvantage on ability checks and attack rolls while source of fear is in sight. Cannot willingly move closer.",
    "drunk": "Disadvantage on finesse and perception checks. Unpredictable tactical decisions.",
    "foolishness": "Ignores cover and tactical defense. Draws enemy threat.",
    "stunned": "Incapacitated, cannot move, can speak only falteringly. Fails Strength and Dexterity saving throws.",
    "poisoned": "Disadvantage on attack rolls and ability checks.",
}
