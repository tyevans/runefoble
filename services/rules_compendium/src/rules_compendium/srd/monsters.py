"""Canonical SRD 5.1 monsters dataset."""

from typing import Any

CANONICAL_MONSTERS: list[dict[str, Any]] = [
    {
        "name": "Goblin",
        "challenge_rating": 0.25,
        "creature_type": "humanoid",
        "size": "Small",
        "armor_class": 15,
        "hit_points": 7,
        "speed": "30 ft.",
        "xp": 50,
        "role": "skirmisher",
        "stats": {"STR": 8, "DEX": 14, "CON": 10, "INT": 10, "WIS": 8, "CHA": 8},
        "description": "Small, black-hearted humanoids that lair in despoiled dungeons and other dismal settings.",
        "traits": [
            {
                "name": "Nimble Escape",
                "description": "Can take Disengage or Hide as a bonus action.",
            }
        ],
        "actions": [
            {
                "name": "Scimitar",
                "description": "Melee Weapon Attack: +4 to hit, reach 5 ft., 1d6+2 slashing.",
            }
        ],
    },
    {
        "name": "Hobgoblin",
        "challenge_rating": 0.5,
        "creature_type": "humanoid",
        "size": "Medium",
        "armor_class": 18,
        "hit_points": 11,
        "speed": "30 ft.",
        "xp": 100,
        "role": "artillery",
        "stats": {"STR": 13, "DEX": 12, "CON": 12, "INT": 10, "WIS": 10, "CHA": 9},
        "description": "Cunning and disciplined warriors who crave conquest.",
        "traits": [
            {
                "name": "Martial Advantage",
                "description": "Deals 2d6 extra damage to a creature if an ally is within 5 ft.",
            }
        ],
        "actions": [
            {
                "name": "Longsword",
                "description": "Melee Weapon Attack: +3 to hit, reach 5 ft., 1d8+1 slashing.",
            },
            {
                "name": "Longbow",
                "description": "Ranged Weapon Attack: +3 to hit, range 150/600 ft., 1d8+1 piercing.",
            },
        ],
    },
    {
        "name": "Bugbear",
        "challenge_rating": 1.0,
        "creature_type": "humanoid",
        "size": "Medium",
        "armor_class": 16,
        "hit_points": 27,
        "speed": "30 ft.",
        "xp": 200,
        "role": "brute",
        "stats": {"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 11, "CHA": 9},
        "description": "Hulking goblinoids that revere strength and stealth.",
        "traits": [
            {"name": "Surprise Attack", "description": "Deals 2d6 extra damage on surprise rounds."}
        ],
        "actions": [
            {
                "name": "Morningstar",
                "description": "Melee Weapon Attack: +4 to hit, reach 5 ft., 2d8+2 piercing.",
            }
        ],
    },
    {
        "name": "Orc",
        "challenge_rating": 0.5,
        "creature_type": "humanoid",
        "size": "Medium",
        "armor_class": 13,
        "hit_points": 15,
        "speed": "30 ft.",
        "xp": 100,
        "role": "brute",
        "stats": {"STR": 16, "DEX": 12, "CON": 16, "INT": 7, "WIS": 11, "CHA": 10},
        "description": "Savage raiders with prominent lower canines and stooped posture.",
        "traits": [
            {
                "name": "Aggressive",
                "description": "Bonus action to move up to speed toward a hostile creature.",
            }
        ],
        "actions": [
            {
                "name": "Greataxe",
                "description": "Melee Weapon Attack: +5 to hit, reach 5 ft., 1d12+3 slashing.",
            }
        ],
    },
    {
        "name": "Ogre",
        "challenge_rating": 2.0,
        "creature_type": "giant",
        "size": "Large",
        "armor_class": 11,
        "hit_points": 59,
        "speed": "40 ft.",
        "xp": 450,
        "role": "brute",
        "stats": {"STR": 19, "DEX": 8, "CON": 16, "INT": 5, "WIS": 7, "CHA": 7},
        "description": "Fierce giants easily enraged by intruders or petty grievances.",
        "traits": [],
        "actions": [
            {
                "name": "Greatclub",
                "description": "Melee Weapon Attack: +6 to hit, reach 5 ft., 2d8+4 bludgeoning.",
            }
        ],
    },
    {
        "name": "Acolyte",
        "challenge_rating": 0.25,
        "creature_type": "humanoid",
        "size": "Medium",
        "armor_class": 10,
        "hit_points": 9,
        "speed": "30 ft.",
        "xp": 50,
        "role": "controller",
        "stats": {"STR": 10, "DEX": 10, "CON": 10, "INT": 10, "WIS": 14, "CHA": 11},
        "description": "Junior clergy member capable of basic divine magic and healing.",
        "traits": [
            {
                "name": "Spellcasting",
                "description": "1st level spellcaster (Wisdom save DC 12). Casts Bless, Cure Wounds.",
            }
        ],
        "actions": [
            {
                "name": "Club",
                "description": "Melee Weapon Attack: +2 to hit, reach 5 ft., 1d4 bludgeoning.",
            }
        ],
    },
    {
        "name": "Mage",
        "challenge_rating": 6.0,
        "creature_type": "humanoid",
        "size": "Medium",
        "armor_class": 12,
        "hit_points": 40,
        "speed": "30 ft.",
        "xp": 2300,
        "role": "controller",
        "stats": {"STR": 9, "DEX": 14, "CON": 11, "INT": 17, "WIS": 12, "CHA": 11},
        "description": "Accomplished spellcaster wielding devastating arcane magic including Fireball and Counterspell.",
        "traits": [
            {
                "name": "Spellcasting",
                "description": "9th-level spellcaster (DC 14, +6 to hit). Spells include Fireball, Cone of Cold, Fly.",
            }
        ],
        "actions": [
            {
                "name": "Dagger",
                "description": "Melee or Ranged Weapon Attack: +5 to hit, reach 5 ft. or range 20/60 ft., 1d4+2 piercing.",
            }
        ],
    },
    {
        "name": "Bandit",
        "challenge_rating": 0.125,
        "creature_type": "humanoid",
        "size": "Medium",
        "armor_class": 12,
        "hit_points": 11,
        "speed": "30 ft.",
        "xp": 25,
        "role": "skirmisher",
        "stats": {"STR": 11, "DEX": 12, "CON": 12, "INT": 10, "WIS": 10, "CHA": 10},
        "description": "Highwaymen and ruthless outlaws preying on unwary travelers.",
        "traits": [],
        "actions": [
            {
                "name": "Scimitar",
                "description": "Melee Weapon Attack: +3 to hit, reach 5 ft., 1d6+1 slashing.",
            }
        ],
    },
    {
        "name": "Skeleton",
        "challenge_rating": 0.25,
        "creature_type": "undead",
        "size": "Medium",
        "armor_class": 13,
        "hit_points": 13,
        "speed": "30 ft.",
        "xp": 50,
        "role": "artillery",
        "stats": {"STR": 10, "DEX": 14, "CON": 15, "INT": 6, "WIS": 8, "CHA": 5},
        "description": "Animated bones of the dead driven by necromantic compulsion.",
        "traits": [
            {
                "name": "Vulnerabilities",
                "description": "Vulnerable to bludgeoning damage; immune to poison.",
            }
        ],
        "actions": [
            {
                "name": "Shortbow",
                "description": "Ranged Weapon Attack: +4 to hit, range 80/320 ft., 1d6+2 piercing.",
            }
        ],
    },
    {
        "name": "Zombie",
        "challenge_rating": 0.25,
        "creature_type": "undead",
        "size": "Medium",
        "armor_class": 8,
        "hit_points": 22,
        "speed": "20 ft.",
        "xp": 50,
        "role": "brute",
        "stats": {"STR": 13, "DEX": 6, "CON": 16, "INT": 3, "WIS": 6, "CHA": 5},
        "description": "Relentless corpse that refuses to stay down unless obliterated.",
        "traits": [
            {
                "name": "Undead Fortitude",
                "description": "When reduced to 0 HP, CON save (DC 5 + damage) to drop to 1 HP instead.",
            }
        ],
        "actions": [
            {
                "name": "Slam",
                "description": "Melee Weapon Attack: +3 to hit, reach 5 ft., 1d6+1 bludgeoning.",
            }
        ],
    },
    {
        "name": "Wolf",
        "challenge_rating": 0.25,
        "creature_type": "beast",
        "size": "Medium",
        "armor_class": 13,
        "hit_points": 11,
        "speed": "40 ft.",
        "xp": 50,
        "role": "skirmisher",
        "stats": {"STR": 12, "DEX": 15, "CON": 12, "INT": 3, "WIS": 12, "CHA": 6},
        "description": "Keen-sensed pack hunter proficient at knocking targets prone.",
        "traits": [
            {
                "name": "Keen Hearing and Smell",
                "description": "Advantage on Perception checks relying on hearing/smell.",
            },
            {
                "name": "Pack Tactics",
                "description": "Advantage on attack rolls if an ally is within 5 ft. of target.",
            },
        ],
        "actions": [
            {
                "name": "Bite",
                "description": "Melee Weapon Attack: +4 to hit, reach 5 ft., 2d4+2 piercing; DC 11 STR save or prone.",
            }
        ],
    },
    {
        "name": "Young Red Dragon",
        "challenge_rating": 10.0,
        "creature_type": "dragon",
        "size": "Large",
        "armor_class": 18,
        "hit_points": 178,
        "speed": "40 ft., climb 40 ft., fly 80 ft.",
        "xp": 5900,
        "role": "boss",
        "stats": {"STR": 23, "DEX": 10, "CON": 21, "INT": 14, "WIS": 11, "CHA": 19},
        "description": "Arrogant, covetous tyrant dragon that incinerates foes with fire breath.",
        "traits": [{"name": "Fire Immunity", "description": "Immune to fire damage."}],
        "actions": [
            {"name": "Multiattack", "description": "Makes three attacks: one bite and two claws."},
            {
                "name": "Fire Breath",
                "description": "Recharge 5-6. 30 ft. cone, DC 17 Dex save, 16d6 fire damage.",
            },
        ],
    },
]
