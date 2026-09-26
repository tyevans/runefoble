"""Autonomous DM Session & Scene Orchestration Engine.

Empowers The Watcher to autonomously set scene atmospheres, balance and spawn tactical
encounters with monster tokens, and adjudicate intelligent NPC/monster tactics.
"""

from typing import Any
from uuid import uuid4

from runefoble_events.events import (
    AutonomousActionResolved,
    EncounterSpawned,
    SceneAtmosphereSet,
)


class AutonomousDMEngine:
    """Core autonomous game master engine for scene atmosphere, encounter balancing, and NPC tactics."""

    SCENE_PRESETS: dict[str, dict[str, Any]] = {
        "dungeon": {
            "name": "Forgotten Underhalls",
            "lighting": "dim flickering torches casting elongated shadows",
            "descriptions": {
                "suspenseful": "Damp stonework glistens under dying torchlight. The distant, rhythmic drip of water echoes like a ticking clock.",
                "eerie": "Chill air drafts up from cracks in flagstones. Pale luminescent mold clings to walls, whispering faintly.",
                "foreboding": "Scratch marks gouge deep into stone walls. Ancient iron portcullises hang bent and battered aside.",
            },
            "ambient_audio": "subterranean dungeon ambiance, distant water dripping, faint low hum, damp echoing cavern",
        },
        "crypt": {
            "name": "Crypt of the Restless Kings",
            "lighting": "pale cold luminescence from weeping wall moss",
            "descriptions": {
                "suspenseful": "Ancient stone sarcophagi line the walls. A bone-chilling draft stirs dry funerary shrouds.",
                "eerie": "Muffled whispers drift from sealed burial niches. Scent of embalming myrrh fills every breath with bitter cold.",
                "foreboding": "Shattered seals on the royal tomb signify a broken ward. Shadows congregate unnaturally around the dais.",
            },
            "ambient_audio": "eerie crypt silence, faint mournful wind, scratching behind stone tombs, low choir drone",
        },
        "tavern": {
            "name": "The Wayward Drake Inn",
            "lighting": "warm hearth glow interspersed with flickering tallow candles",
            "descriptions": {
                "suspenseful": "Heavy oak beams creak overhead as roasted meat scents mingle with uneasy murmurs among cloaked patrons.",
                "eerie": "The tavern patrons stare blankly into untouched ale. Even the roaring fire produces no comforting warmth.",
                "cozy": "A roaring hearth crackles merrily. The bard strums a lively ballad as tankards clatter in hearty toasts.",
            },
            "ambient_audio": "busy medieval tavern background noise, clinking flagons, muffled hearth fire crackle",
        },
        "forest": {
            "name": "Whispering Pines of Eldermoor",
            "lighting": "dappled moonlight piercing through gnarled pine canopy",
            "descriptions": {
                "suspenseful": "Thick silver fog coils around roots. Nocturnal creatures fall dead silent as unnatural frost creeps.",
                "eerie": "Twisted branches form gaunt silhouettes against twilight. Faint spirit lights dance between briars.",
                "foreboding": "Giant claw ruts tear through mossy bark. Scent of ozone and predator musk signals a prowling apex beast.",
            },
            "ambient_audio": "deep forest night wind, rustling pine needles, distant hoot of an owl, ominous creaking branches",
        },
        "dragon_lair": {
            "name": "Scorched Crag of the Wyrm",
            "lighting": "smoldering magma fissures casting an intense crimson gleam",
            "descriptions": {
                "suspenseful": "Charred dragon scales crunch underfoot. The acrid stench of sulfur hangs thick with cavernous exhalations.",
                "eerie": "Gleaming treasures are fused into glassy obsidian walls. The heat is suffocating, yet icy dread grips the heart.",
                "deadly": "Molten rivers pulse with violent fury. Towering stalactites tremble as massive wings unfurl above.",
            },
            "ambient_audio": "volcanic cave rumble, magma bubbling, distant low reptile breathing, crackling ember heat",
        },
    }

    def set_scene(
        self,
        session_id: str,
        location_type: str = "dungeon",
        mood: str = "suspenseful",
    ) -> SceneAtmosphereSet:
        """Set dynamic scene atmosphere, location details, lighting, and ambient audio prompt."""
        loc_key = location_type.lower().strip().replace(" ", "_")
        mood_key = mood.lower().strip()

        preset = self.SCENE_PRESETS.get(loc_key)
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
            description = f"The party stands within the {clean_name}. A palpable {mood_key} tension pervades every shadow."
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

    def spawn_encounter(
        self,
        session_id: str,
        scene_id: str,
        party_level: int = 3,
        party_size: int = 4,
        difficulty: str = "medium",
    ) -> EncounterSpawned:
        """Calculate challenge rating, balance monsters, and generate an encounter with tactical objectives."""
        diff = difficulty.lower().strip()
        threat_level = diff if diff in {"easy", "medium", "hard", "deadly"} else "medium"
        encounter_id = f"enc-{uuid4().hex[:8]}"
        monsters: list[dict[str, Any]] = []

        if party_level <= 4:
            if threat_level == "easy":
                encounter_name = "Goblin Scout Ambush"
                tactical_objective = "Disperse the scout vanguard before they blow the alarm horn."
                monsters = [
                    {
                        "id": f"{encounter_id}-mon-1",
                        "name": "Goblin Skirmisher",
                        "cr": "1/4",
                        "hp": 7,
                        "max_hp": 7,
                        "ac": 15,
                        "role": "skirmisher",
                        "position": {"x": 8, "y": 3},
                    },
                    {
                        "id": f"{encounter_id}-mon-2",
                        "name": "Goblin Archer",
                        "cr": "1/4",
                        "hp": 7,
                        "max_hp": 7,
                        "ac": 13,
                        "role": "ranged",
                        "position": {"x": 10, "y": 2},
                    },
                ]
            elif threat_level == "hard":
                encounter_name = "Crypt Guardian Vanguard"
                tactical_objective = (
                    "Defeat the Bugbear Chieftain before the archers pin the frontline down."
                )
                monsters = [
                    {
                        "id": f"{encounter_id}-mon-1",
                        "name": "Bugbear Chieftain",
                        "cr": "3",
                        "hp": 65,
                        "max_hp": 65,
                        "ac": 17,
                        "role": "bruiser",
                        "position": {"x": 6, "y": 5},
                    },
                    {
                        "id": f"{encounter_id}-mon-2",
                        "name": "Skeleton Archer Alpha",
                        "cr": "1/4",
                        "hp": 13,
                        "max_hp": 13,
                        "ac": 13,
                        "role": "ranged",
                        "position": {"x": 9, "y": 2},
                    },
                    {
                        "id": f"{encounter_id}-mon-3",
                        "name": "Skeleton Archer Beta",
                        "cr": "1/4",
                        "hp": 13,
                        "max_hp": 13,
                        "ac": 13,
                        "role": "ranged",
                        "position": {"x": 9, "y": 8},
                    },
                ]
            elif threat_level == "deadly":
                encounter_name = "Shadow Wraith Stalker"
                tactical_objective = (
                    "Neutralize the Wraith before life-drain reduces party constitution to zero."
                )
                monsters = [
                    {
                        "id": f"{encounter_id}-mon-1",
                        "name": "Grave Wraith",
                        "cr": "5",
                        "hp": 67,
                        "max_hp": 67,
                        "ac": 13,
                        "role": "caster",
                        "position": {"x": 7, "y": 6},
                    },
                    {
                        "id": f"{encounter_id}-mon-2",
                        "name": "Crawling Shadow",
                        "cr": "1/2",
                        "hp": 16,
                        "max_hp": 16,
                        "ac": 12,
                        "role": "skirmisher",
                        "position": {"x": 5, "y": 4},
                    },
                ]
            else:  # medium
                encounter_name = "Cavern Skirmish Squad"
                tactical_objective = (
                    "Eliminate the frontline warriors and isolate the goblin shaman."
                )
                monsters = [
                    {
                        "id": f"{encounter_id}-mon-1",
                        "name": "Goblin Boss",
                        "cr": "1",
                        "hp": 21,
                        "max_hp": 21,
                        "ac": 17,
                        "role": "boss",
                        "position": {"x": 7, "y": 5},
                    },
                    {
                        "id": f"{encounter_id}-mon-2",
                        "name": "Goblin Shaman",
                        "cr": "1",
                        "hp": 18,
                        "max_hp": 18,
                        "ac": 12,
                        "role": "caster",
                        "position": {"x": 10, "y": 5},
                    },
                    {
                        "id": f"{encounter_id}-mon-3",
                        "name": "Goblin Cutthroat",
                        "cr": "1/4",
                        "hp": 9,
                        "max_hp": 9,
                        "ac": 14,
                        "role": "skirmisher",
                        "position": {"x": 6, "y": 4},
                    },
                ]
        else:
            encounter_name = "Infernal Drake Reckoning"
            tactical_objective = (
                "Sever the drake's fire breath rhythm by disrupting its grounding stance."
            )
            monsters = [
                {
                    "id": f"{encounter_id}-mon-1",
                    "name": "Young Red Dragon",
                    "cr": "10",
                    "hp": 178,
                    "max_hp": 178,
                    "ac": 18,
                    "role": "boss",
                    "position": {"x": 8, "y": 8},
                },
                {
                    "id": f"{encounter_id}-mon-2",
                    "name": "Fire Cultist Zealot",
                    "cr": "2",
                    "hp": 45,
                    "max_hp": 45,
                    "ac": 15,
                    "role": "caster",
                    "position": {"x": 11, "y": 6},
                },
            ]

        if party_size >= 5 and len(monsters) < 4:
            extra_idx = len(monsters) + 1
            monsters.append(
                {
                    "id": f"{encounter_id}-mon-{extra_idx}",
                    "name": "Reinforcement Minion",
                    "cr": "1/4",
                    "hp": 11,
                    "max_hp": 11,
                    "ac": 13,
                    "role": "minion",
                    "position": {"x": 5, "y": 7},
                }
            )

        return EncounterSpawned(
            session_id=session_id,
            encounter_id=encounter_id,
            encounter_name=encounter_name,
            threat_level=threat_level,
            monsters=monsters,
            tactical_objective=tactical_objective,
        )

    def resolve_npc_turn(
        self,
        session_id: str,
        encounter_id: str,
        actor_name: str,
        targets: list[dict[str, Any]],
        round_number: int = 1,
    ) -> AutonomousActionResolved:
        """Adjudicate tactical combat decision tree for an NPC or monster."""
        if not targets:
            return AutonomousActionResolved(
                session_id=session_id,
                actor_name=actor_name,
                action_type="search",
                target_name="None",
                narrative=f"{actor_name} scans the shadows in round {round_number}, seeking active threats.",
                hp_impact=0,
            )

        valid_targets = [t for t in targets if t.get("current_hp", t.get("hp", 1)) > 0] or targets
        sorted_targets = sorted(valid_targets, key=lambda t: t.get("current_hp", t.get("hp", 100)))
        chosen_target = sorted_targets[0]
        target_name = chosen_target.get("name", "the party hero")
        target_hp = chosen_target.get("current_hp", chosen_target.get("hp", 20))

        actor_lower = actor_name.lower()
        is_caster = any(
            kw in actor_lower
            for kw in [
                "shaman",
                "mage",
                "caster",
                "wraith",
                "cultist",
                "priest",
                "lich",
                "witch",
                "wizard",
            ]
        )

        if is_caster:
            action_type = "cast_spell"
            spell_names = [
                "Ray of Enfeeblement",
                "Shadow Bolt",
                "Misty Step & Fire Bolt",
                "Chaos Spark",
            ]
            chosen_spell = spell_names[(round_number - 1) % len(spell_names)]
            hp_impact = -8
            narrative = (
                f"{actor_name} channels forbidden incantations in round {round_number}, unleashing {chosen_spell} "
                f"directly into {target_name} for {abs(hp_impact)} necrotic damage!"
            )
        elif target_hp <= 10:
            action_type = "execute_strike"
            hp_impact = -10
            narrative = (
                f"Sensing vulnerability, {actor_name} lunges at the heavily wounded {target_name} with ruthless "
                f"precision, delivering a finishing blow for {abs(hp_impact)} damage!"
            )
        elif round_number == 1:
            action_type = "charge_attack"
            hp_impact = -6
            narrative = (
                f"{actor_name} breaks from cover in an aggressive charge, slamming their weapon toward {target_name}'s "
                f"exposed flank for {abs(hp_impact)} damage!"
            )
        else:
            action_type = "melee_strike"
            hp_impact = -7
            narrative = (
                f"{actor_name} strikes forcefully against {target_name} in round {round_number}, "
                f"inflicting {abs(hp_impact)} slashing damage!"
            )

        return AutonomousActionResolved(
            session_id=session_id,
            actor_name=actor_name,
            action_type=action_type,
            target_name=target_name,
            narrative=narrative,
            hp_impact=hp_impact,
        )
