"""Autonomous DM Session & Scene Orchestration Engine Facade.

Empowers The Watcher to autonomously set scene atmospheres, balance and spawn tactical
encounters with monster tokens, and adjudicate intelligent NPC/monster tactics.
Orchestrates modular presets, encounters, and tactics domain submodules.
"""

from __future__ import annotations

from typing import Any

from runefoble_events.events import (
    AutonomousActionResolved,
    EncounterSpawned,
    SceneAtmosphereSet,
)
from the_watcher.encounters import build_encounter
from the_watcher.presets import SCENE_PRESETS, build_scene_atmosphere
from the_watcher.tactics import adjudicate_npc_turn

__all__ = [
    "AutonomousDMEngine",
    "SCENE_PRESETS",
    "build_scene_atmosphere",
    "build_encounter",
    "adjudicate_npc_turn",
]


class AutonomousDMEngine:
    """Core autonomous game master engine for scene atmosphere, encounter balancing, and NPC tactics."""

    SCENE_PRESETS: dict[str, dict[str, Any]] = SCENE_PRESETS

    def set_scene(
        self,
        session_id: str,
        location_type: str = "dungeon",
        mood: str = "suspenseful",
    ) -> SceneAtmosphereSet:
        """Set dynamic scene atmosphere, location details, lighting, and ambient audio prompt."""
        return build_scene_atmosphere(
            session_id=session_id,
            location_type=location_type,
            mood=mood,
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
        return build_encounter(
            session_id=session_id,
            scene_id=scene_id,
            party_level=party_level,
            party_size=party_size,
            difficulty=difficulty,
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
        return adjudicate_npc_turn(
            session_id=session_id,
            encounter_id=encounter_id,
            actor_name=actor_name,
            targets=targets,
            round_number=round_number,
        )
