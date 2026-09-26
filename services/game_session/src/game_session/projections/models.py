"""Denormalized read models for Game Session projections."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class TokenReadModel(BaseModel):
    """Denormalized read model for a token on the grid."""

    token_id: str
    name: str
    x: int
    y: int
    token_type: str = "pc"
    hp: int | None = None
    is_friendly: bool = False


class AtmosphereReadModel(BaseModel):
    """Denormalized read model for scene atmosphere and lighting."""

    scene_id: str
    location_name: str
    lighting: str = ""
    mood: str = ""
    description: str = ""
    ambient_audio_prompt: str = ""


class EncounterReadModel(BaseModel):
    """Denormalized read model for active combat or narrative encounters."""

    encounter_id: str
    encounter_name: str
    threat_level: str
    monsters: list[dict[str, Any]] = Field(default_factory=list)
    tactical_objective: str = ""
    active: bool = True


class CombatantInitiativeModel(BaseModel):
    """Denormalized read model for a combatant in initiative order."""

    combatant_id: str
    combatant_name: str
    initiative_score: float | int
    is_npc: bool = False


class InitiativeReadModel(BaseModel):
    """Denormalized read model for combat initiative and turn order."""

    session_id: str
    in_combat: bool = False
    combat_round: int = 1
    combat_active_id: str | None = None
    initiative_order: list[CombatantInitiativeModel] = Field(default_factory=list)
    turn_seconds_remaining: int = 60
    last_updated_at: str | None = None


class ParticipantPresenceModel(BaseModel):
    """Denormalized read model for participant presence and connection status."""

    player_id: str
    character_id: str | None = None
    character_name: str | None = None
    character_class: str | None = None
    is_present: bool = True
    is_stand_in_active: bool = False
    last_seen_at: str | None = None


class PresenceReadModel(BaseModel):
    """Denormalized read model for session participants and spectator presence."""

    session_id: str
    participants: dict[str, ParticipantPresenceModel] = Field(default_factory=dict)
    spectator_count: int = 0
    last_updated_at: str | None = None


class SessionReadModel(BaseModel):
    """Denormalized full session read model for low-latency queries."""

    session_id: str
    title: str = "Untitled Session"
    status: str = "lobby"
    current_turn: int = 1
    tokens: dict[str, TokenReadModel] = Field(default_factory=dict)
    atmosphere: AtmosphereReadModel | None = None
    encounters: dict[str, EncounterReadModel] = Field(default_factory=dict)
    combat_log: list[dict[str, Any]] = Field(default_factory=list)
    event_count: int = 0
    last_updated_at: str | None = None


__all__ = [
    "TokenReadModel",
    "AtmosphereReadModel",
    "EncounterReadModel",
    "CombatantInitiativeModel",
    "InitiativeReadModel",
    "ParticipantPresenceModel",
    "PresenceReadModel",
    "SessionReadModel",
]
