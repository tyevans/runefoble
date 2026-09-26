"""Event projection workers for Game Session service read models."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field
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
from runefoble_platform.consumer_group import RedisConsumerGroup
from runefoble_platform.models import utc_now

logger = logging.getLogger("runefoble.game_session.projections")


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


class SessionReadProjection:
    """Projects distributed stream events into an in-memory or persisted denormalized read model."""

    def __init__(
        self,
        consumer_group: RedisConsumerGroup | None = None,
        stream: str = "runefoble.events.session",
        group_name: str = "session_projection_workers",
        consumer_name: str = "proj_worker_1",
    ) -> None:
        self.consumer_group = consumer_group
        self.stream = stream
        self.group_name = group_name
        self.consumer_name = consumer_name
        self.sessions: dict[str, SessionReadModel] = {}
        self.running: bool = False
        self._task: asyncio.Task[None] | None = None

    def _extract_session_id(self, event: Any) -> str:
        if isinstance(event, dict):
            return str(event.get("session_id") or event.get("session_id_str") or event.get("aggregate_id") or "default")
        return str(
            getattr(event, "session_id", None)
            or getattr(event, "session_id_str", None)
            or getattr(event, "aggregate_id", None)
            or "default"
        )

    def apply_event(self, event: Any) -> None:
        """Apply a domain event or event dictionary to update the denormalized read model."""
        session_id = self._extract_session_id(event)
        session = self.sessions.setdefault(session_id, SessionReadModel(session_id=session_id))

        if isinstance(event, TokenPlaced):
            session.tokens[event.token_id] = TokenReadModel(
                token_id=event.token_id, name=event.name, x=event.x, y=event.y,
                token_type=event.token_type, hp=event.hp, is_friendly=event.is_friendly,
            )
        elif isinstance(event, TokenMoved):
            if event.token_id in session.tokens:
                session.tokens[event.token_id].x, session.tokens[event.token_id].y = event.to_x, event.to_y
            else:
                session.tokens[event.token_id] = TokenReadModel(
                    token_id=event.token_id, name=event.name, x=event.to_x, y=event.to_y,
                )
        elif isinstance(event, TokenRemoved):
            session.tokens.pop(event.token_id, None)
        elif isinstance(event, SceneAtmosphereSet):
            session.atmosphere = AtmosphereReadModel(
                scene_id=event.scene_id, location_name=event.location_name,
                lighting=event.lighting, mood=event.mood, description=event.description,
                ambient_audio_prompt=event.ambient_audio_prompt,
            )
        elif isinstance(event, EncounterSpawned):
            session.encounters[event.encounter_id] = EncounterReadModel(
                encounter_id=event.encounter_id, encounter_name=event.encounter_name,
                threat_level=event.threat_level, monsters=event.monsters,
                tactical_objective=event.tactical_objective, active=True,
            )
        elif isinstance(event, AutonomousActionResolved):
            session.combat_log.append({
                "actor_name": event.actor_name, "action_type": event.action_type,
                "target_name": event.target_name, "narrative": event.narrative, "hp_impact": event.hp_impact,
            })
        elif isinstance(event, TurnAdvanced):
            session.current_turn = getattr(event, "new_turn", getattr(event, "current_turn", session.current_turn + 1))
        elif isinstance(event, SessionCreated):
            session.title = event.title
        elif isinstance(event, SessionStarted):
            session.status = "active"
        elif isinstance(event, SessionEnded):
            session.status = "ended"
        elif isinstance(event, dict):
            self._apply_dict_event(session, event)

        session.event_count += 1
        session.last_updated_at = utc_now().isoformat()

    def _apply_dict_event(self, session: SessionReadModel, event: dict[str, Any]) -> None:
        event_type = event.get("event_type") or event.get("type") or ""
        if "TokenPlaced" in event_type:
            token_id = str(event.get("token_id", ""))
            session.tokens[token_id] = TokenReadModel(
                token_id=token_id, name=event.get("name", "Token"),
                x=int(event.get("x", 0)), y=int(event.get("y", 0)),
                token_type=event.get("token_type", "pc"), hp=event.get("hp"),
                is_friendly=bool(event.get("is_friendly", False)),
            )
        elif "TokenMoved" in event_type:
            token_id, to_x, to_y = str(event.get("token_id", "")), int(event.get("to_x", 0)), int(event.get("to_y", 0))
            if token_id in session.tokens:
                session.tokens[token_id].x, session.tokens[token_id].y = to_x, to_y
            else:
                session.tokens[token_id] = TokenReadModel(token_id=token_id, name=event.get("name", "Unknown"), x=to_x, y=to_y)
        elif "TokenRemoved" in event_type:
            session.tokens.pop(str(event.get("token_id", "")), None)
        elif "SceneAtmosphereSet" in event_type or "atmosphere_set" in event_type:
            session.atmosphere = AtmosphereReadModel(
                scene_id=str(event.get("scene_id", "scene_1")),
                location_name=str(event.get("location_name", "")),
                lighting=str(event.get("lighting", "")), mood=str(event.get("mood", "")),
                description=str(event.get("description", "")),
                ambient_audio_prompt=str(event.get("ambient_audio_prompt", "")),
            )
        elif "EncounterSpawned" in event_type or "encounter.spawned" in event_type:
            encounter_id = str(event.get("encounter_id", "enc_1"))
            session.encounters[encounter_id] = EncounterReadModel(
                encounter_id=encounter_id, encounter_name=str(event.get("encounter_name", "Encounter")),
                threat_level=str(event.get("threat_level", "medium")), monsters=list(event.get("monsters", [])),
                tactical_objective=str(event.get("tactical_objective", "")), active=True,
            )

    async def process_once(self, count: int = 10, block_ms: int = 200) -> int:
        """Poll the consumer group, project events, and ACK or route poison messages to DLQ."""
        if not self.consumer_group:
            return 0
        messages = await self.consumer_group.read_group(
            stream=self.stream, group_name=self.group_name,
            consumer_name=self.consumer_name, count=count, block_ms=block_ms,
        )
        processed = 0
        for msg_id, event in messages:
            try:
                self.apply_event(event)
                await self.consumer_group.ack(self.stream, self.group_name, msg_id)
                processed += 1
            except Exception as e:
                logger.error("Failed to project message %s: %s", msg_id, e)
                await self.consumer_group.route_to_dead_letter(
                    stream=self.stream, message_id=msg_id, payload=event, error_reason=str(e),
                )
                await self.consumer_group.ack(self.stream, self.group_name, msg_id)
        return processed

    async def start(self) -> None:
        """Initialize consumer group and start background processing loop."""
        if self.consumer_group:
            await self.consumer_group.create_group(self.stream, self.group_name)
        self.running = True
        self._task = asyncio.create_task(self._run_loop())

    async def stop(self) -> None:
        """Gracefully stop background loop."""
        self.running = False
        if self._task and not self._task.done():
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None

    async def _run_loop(self) -> None:
        while self.running:
            try:
                await self.process_once()
                await asyncio.sleep(0.01)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception("Error in projection worker loop: %s", e)
                await asyncio.sleep(0.1)

    def get_session(self, session_id: str | UUID) -> SessionReadModel | None:
        return self.sessions.get(str(session_id))

    def get_tokens(self, session_id: str | UUID) -> dict[str, TokenReadModel]:
        session = self.get_session(session_id)
        return session.tokens if session else {}

    def get_token(self, session_id: str | UUID, token_id: str) -> TokenReadModel | None:
        return self.get_tokens(session_id).get(str(token_id))

    def get_atmosphere(self, session_id: str | UUID) -> AtmosphereReadModel | None:
        session = self.get_session(session_id)
        return session.atmosphere if session else None

    def get_encounters(self, session_id: str | UUID) -> dict[str, EncounterReadModel]:
        session = self.get_session(session_id)
        return session.encounters if session else {}

    def get_combat_log(self, session_id: str | UUID) -> list[dict[str, Any]]:
        session = self.get_session(session_id)
        return session.combat_log if session else []
