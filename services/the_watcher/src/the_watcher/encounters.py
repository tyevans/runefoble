"""Autonomous DM Encounter Balancing & Monster Spawning.

Manages encounter balancing, threat rating scaling, monster stat templates,
and tactical objectives.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from runefoble_events.events import EncounterSpawned


def _build_monster(
    encounter_id: str,
    idx: int,
    name: str,
    cr: str,
    hp: int,
    ac: int,
    role: str,
    pos: tuple[int, int],
) -> dict[str, Any]:
    return {
        "id": f"{encounter_id}-mon-{idx}",
        "name": name,
        "cr": cr,
        "hp": hp,
        "max_hp": hp,
        "ac": ac,
        "role": role,
        "position": {"x": pos[0], "y": pos[1]},
    }


def _tier1_encounter(threat_level: str, enc_id: str) -> tuple[str, str, list[dict[str, Any]]]:
    if threat_level == "easy":
        name = "Goblin Scout Ambush"
        objective = "Disperse the scout vanguard before they blow the alarm horn."
        monsters = [
            _build_monster(enc_id, 1, "Goblin Skirmisher", "1/4", 7, 15, "skirmisher", (8, 3)),
            _build_monster(enc_id, 2, "Goblin Archer", "1/4", 7, 13, "ranged", (10, 2)),
        ]
    elif threat_level == "hard":
        name = "Crypt Guardian Vanguard"
        objective = "Defeat the Bugbear Chieftain before the archers pin the frontline down."
        monsters = [
            _build_monster(enc_id, 1, "Bugbear Chieftain", "3", 65, 17, "bruiser", (6, 5)),
            _build_monster(enc_id, 2, "Skeleton Archer Alpha", "1/4", 13, 13, "ranged", (9, 2)),
            _build_monster(enc_id, 3, "Skeleton Archer Beta", "1/4", 13, 13, "ranged", (9, 8)),
        ]
    elif threat_level == "deadly":
        name = "Shadow Wraith Stalker"
        objective = "Neutralize the Wraith before life-drain reduces party constitution to zero."
        monsters = [
            _build_monster(enc_id, 1, "Grave Wraith", "5", 67, 13, "caster", (7, 6)),
            _build_monster(enc_id, 2, "Crawling Shadow", "1/2", 16, 12, "skirmisher", (5, 4)),
        ]
    else:  # medium
        name = "Cavern Skirmish Squad"
        objective = "Eliminate the frontline warriors and isolate the goblin shaman."
        monsters = [
            _build_monster(enc_id, 1, "Goblin Boss", "1", 21, 17, "boss", (7, 5)),
            _build_monster(enc_id, 2, "Goblin Shaman", "1", 18, 12, "caster", (10, 5)),
            _build_monster(enc_id, 3, "Goblin Cutthroat", "1/4", 9, 14, "skirmisher", (6, 4)),
        ]
    return name, objective, monsters


def build_encounter(
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

    if party_level <= 4:
        name, objective, monsters = _tier1_encounter(threat_level, encounter_id)
    else:
        name = "Infernal Drake Reckoning"
        objective = "Sever the drake's fire breath rhythm by disrupting its grounding stance."
        monsters = [
            _build_monster(encounter_id, 1, "Young Red Dragon", "10", 178, 18, "boss", (8, 8)),
            _build_monster(encounter_id, 2, "Fire Cultist Zealot", "2", 45, 15, "caster", (11, 6)),
        ]

    if party_size >= 5 and len(monsters) < 4:
        monsters.append(
            _build_monster(
                encounter_id,
                len(monsters) + 1,
                "Reinforcement Minion",
                "1/4",
                11,
                13,
                "minion",
                (5, 7),
            )
        )

    return EncounterSpawned(
        session_id=session_id,
        encounter_id=encounter_id,
        encounter_name=name,
        threat_level=threat_level,
        monsters=monsters,
        tactical_objective=objective,
    )
