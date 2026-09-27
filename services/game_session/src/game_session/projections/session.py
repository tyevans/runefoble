"""Session read model event projection worker and background processor."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from typing import Any
from uuid import UUID

from game_session.projections.appliers import apply_session_event
from game_session.projections.initiative import InitiativeProjection
from game_session.projections.models import (
    AtmosphereReadModel,
    EncounterReadModel,
    InitiativeReadModel,
    PresenceReadModel,
    SessionReadModel,
    TokenReadModel,
)
from game_session.projections.presence import PresenceProjection
from runefoble_platform.consumer_group import RedisConsumerGroup
from runefoble_platform.models import utc_now

logger = logging.getLogger("runefoble.game_session.projections.session")


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
        self.initiative = InitiativeProjection()
        self.presence = PresenceProjection()
        self.running: bool = False
        self._task: asyncio.Task[None] | None = None

    def _extract_session_id(self, event: Any) -> str:
        if isinstance(event, dict):
            return str(
                event.get("session_id")
                or event.get("session_id_str")
                or event.get("aggregate_id")
                or "default"
            )
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

        apply_session_event(session, event)
        self.initiative.apply_event(event)
        self.presence.apply_event(event)

        session.event_count += 1
        session.last_updated_at = utc_now().isoformat()

    async def process_once(self, count: int = 10, block_ms: int = 200) -> int:
        """Poll consumer group, project events, and ACK or route poison messages to DLQ."""
        if not self.consumer_group:
            return 0
        messages = await self.consumer_group.read_group(
            stream=self.stream,
            group_name=self.group_name,
            consumer_name=self.consumer_name,
            count=count,
            block_ms=block_ms,
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
                    stream=self.stream, message_id=msg_id, payload=event, error_reason=str(e)
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

    def get_initiative(self, session_id: str | UUID) -> InitiativeReadModel | None:
        return self.initiative.get_initiative(session_id)

    def get_presence(self, session_id: str | UUID) -> PresenceReadModel | None:
        return self.presence.get_presence(session_id)


__all__ = ["SessionReadProjection"]
