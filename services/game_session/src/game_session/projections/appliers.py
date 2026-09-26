"""Event appliers for updating session read models from stream events."""

from __future__ import annotations

from typing import Any

from game_session.projections.models import (
    AtmosphereReadModel,
    EncounterReadModel,
    SessionReadModel,
    TokenReadModel,
)
from runefoble_events.events import (
    AutonomousActionResolved,
    EncounterSpawned,
    SceneAtmosphereSet,
    SessionCreated,
    SessionEnded,
    SessionStarted,
    TokenMoved,
    TokenPlaced,
    TokenRemoved,
    TurnAdvanced,
)


def apply_session_event(session: SessionReadModel, event: Any) -> None:
    """Apply domain event or dict to update session, token, atmosphere, and encounter state."""
    if isinstance(event, TokenPlaced):
        session.tokens[event.token_id] = TokenReadModel(
            token_id=event.token_id,
            name=event.name,
            x=event.x,
            y=event.y,
            token_type=event.token_type,
            hp=event.hp,
            is_friendly=event.is_friendly,
        )
    elif isinstance(event, TokenMoved):
        if event.token_id in session.tokens:
            session.tokens[event.token_id].x, session.tokens[event.token_id].y = (
                event.to_x,
                event.to_y,
            )
        else:
            session.tokens[event.token_id] = TokenReadModel(
                token_id=event.token_id, name=event.name, x=event.to_x, y=event.to_y
            )
    elif isinstance(event, TokenRemoved):
        session.tokens.pop(event.token_id, None)
    elif isinstance(event, SceneAtmosphereSet):
        session.atmosphere = AtmosphereReadModel(
            scene_id=event.scene_id,
            location_name=event.location_name,
            lighting=event.lighting,
            mood=event.mood,
            description=event.description,
            ambient_audio_prompt=event.ambient_audio_prompt,
        )
    elif isinstance(event, EncounterSpawned):
        session.encounters[event.encounter_id] = EncounterReadModel(
            encounter_id=event.encounter_id,
            encounter_name=event.encounter_name,
            threat_level=event.threat_level,
            monsters=event.monsters,
            tactical_objective=event.tactical_objective,
            active=True,
        )
    elif isinstance(event, AutonomousActionResolved):
        session.combat_log.append(
            {
                "actor_name": event.actor_name,
                "action_type": event.action_type,
                "target_name": event.target_name,
                "narrative": event.narrative,
                "hp_impact": event.hp_impact,
            }
        )
    elif isinstance(event, TurnAdvanced):
        session.current_turn = getattr(
            event, "new_turn", getattr(event, "current_turn", session.current_turn + 1)
        )
    elif isinstance(event, SessionCreated):
        session.title = event.title
    elif isinstance(event, SessionStarted):
        session.status = "active"
    elif isinstance(event, SessionEnded):
        session.status = "ended"
    elif isinstance(event, dict):
        _apply_dict_event(session, event)


def _apply_dict_event(session: SessionReadModel, event: dict[str, Any]) -> None:
    event_type = event.get("event_type") or event.get("type") or ""
    if "TokenPlaced" in event_type:
        token_id = str(event.get("token_id", ""))
        session.tokens[token_id] = TokenReadModel(
            token_id=token_id,
            name=event.get("name", "Token"),
            x=int(event.get("x", 0)),
            y=int(event.get("y", 0)),
            token_type=event.get("token_type", "pc"),
            hp=event.get("hp"),
            is_friendly=bool(event.get("is_friendly", False)),
        )
    elif "TokenMoved" in event_type:
        token_id, to_x, to_y = (
            str(event.get("token_id", "")),
            int(event.get("to_x", 0)),
            int(event.get("to_y", 0)),
        )
        if token_id in session.tokens:
            session.tokens[token_id].x, session.tokens[token_id].y = to_x, to_y
        else:
            session.tokens[token_id] = TokenReadModel(
                token_id=token_id, name=event.get("name", "Unknown"), x=to_x, y=to_y
            )
    elif "TokenRemoved" in event_type:
        session.tokens.pop(str(event.get("token_id", "")), None)
    elif "SceneAtmosphereSet" in event_type or "atmosphere_set" in event_type:
        session.atmosphere = AtmosphereReadModel(
            scene_id=str(event.get("scene_id", "scene_1")),
            location_name=str(event.get("location_name", "")),
            lighting=str(event.get("lighting", "")),
            mood=str(event.get("mood", "")),
            description=str(event.get("description", "")),
            ambient_audio_prompt=str(event.get("ambient_audio_prompt", "")),
        )
    elif "EncounterSpawned" in event_type or "encounter.spawned" in event_type:
        encounter_id = str(event.get("encounter_id", "enc_1"))
        session.encounters[encounter_id] = EncounterReadModel(
            encounter_id=encounter_id,
            encounter_name=str(event.get("encounter_name", "Encounter")),
            threat_level=str(event.get("threat_level", "medium")),
            monsters=list(event.get("monsters", [])),
            tactical_objective=str(event.get("tactical_objective", "")),
            active=True,
        )


__all__ = ["apply_session_event"]
