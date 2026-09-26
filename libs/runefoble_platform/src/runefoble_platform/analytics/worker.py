"""Background Redis Streams consumer worker translating domain events to OpenPanel metrics."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from typing import Any

from eventsource.domain.event import DomainEvent
from pydantic import BaseModel
from runefoble_events.events import (
    AbsencePenaltyApplied,
    DiceRolled,
    PlayerJoinedSession,
    PlayerLeftSession,
    SessionCreated,
    SessionEnded,
    SessionStarted,
    StandInActionDecided,
)

from runefoble_platform.analytics.client import OpenPanelClient
from runefoble_platform.consumer_group import RedisConsumerGroup

logger = logging.getLogger(__name__)


class AnalyticsEventWorker:
    """Asynchronous background worker translating Redis Streams domain events into OpenPanel telemetry."""

    def __init__(
        self,
        client: OpenPanelClient | None = None,
        consumer_group: RedisConsumerGroup | None = None,
        streams: list[str] | str | None = None,
        group_name: str = "runefoble_analytics_workers",
        consumer_name: str = "analytics_worker_1",
        batch_size: int = 10,
        poll_interval_ms: int = 200,
    ) -> None:
        self.client = client or OpenPanelClient()
        self.consumer_group = consumer_group
        if streams is None:
            self.streams = ["runefoble.events.session", "runefoble.events.watcher"]
        elif isinstance(streams, str):
            self.streams = [streams]
        else:
            self.streams = list(streams)

        self.group_name = group_name
        self.consumer_name = consumer_name
        self.batch_size = batch_size
        self.poll_interval_ms = poll_interval_ms
        self.running: bool = False
        self._task: asyncio.Task[None] | None = None
        self.processed_count: int = 0

    async def setup_groups(self) -> None:
        """Ensure consumer groups exist across all monitored streams."""
        if not self.consumer_group:
            return
        for stream in self.streams:
            await self.consumer_group.create_group(
                stream=stream,
                group_name=self.group_name,
                start_id="0",
                make_stream=True,
            )

    def map_event_to_analytics(self, event: Any) -> tuple[str, dict[str, Any], str | None] | None:
        """Translate a domain event or stream payload dictionary into an OpenPanel metric."""
        sid = str(
            self._get_attr(event, "session_id")
            or self._get_attr(event, "aggregate_id")
            or "default"
        )

        if isinstance(event, SessionStarted) or self._is_type(
            event, ["SessionStarted", "GameSessionStarted", "runefoble.events.session.started"]
        ):
            dm = self._get_attr(event, "dm_id") or self._get_attr(event, "user_id")
            started_at = int(self._get_attr(event, "started_at_turn", 1))
            return (
                "session.started",
                {"session_id": sid, "started_at_turn": started_at},
                str(dm) if dm else None,
            )

        if isinstance(event, SessionCreated) or self._is_type(
            event, ["SessionCreated", "runefoble.events.session.created"]
        ):
            dm = self._get_attr(event, "dm_id", "the_watcher")
            return (
                "session.created",
                {"session_id": sid, "dm_id": str(dm)},
                str(dm) if dm else None,
            )

        if isinstance(event, SessionEnded) or self._is_type(
            event, ["SessionEnded", "runefoble.events.session.ended"]
        ):
            return (
                "session.ended",
                {
                    "session_id": sid,
                    "summary": str(self._get_attr(event, "summary", "Session completed")),
                },
                None,
            )

        if isinstance(event, DiceRolled) or self._is_type(
            event, ["DiceRolled", "DiceRollEvent", "runefoble.events.dice.rolled"]
        ):
            roller = self._get_attr(event, "roller_id")
            return (
                "dice.rolled",
                {
                    "session_id": str(self._get_attr(event, "session_id", sid)),
                    "formula": str(self._get_attr(event, "formula", "")),
                    "total": int(self._get_attr(event, "total", 0)),
                    "is_crit": bool(self._get_attr(event, "is_crit", False)),
                    "is_fumble": bool(self._get_attr(event, "is_fumble", False)),
                    "roll_type": str(self._get_attr(event, "roll_type", "general")),
                },
                str(roller) if roller else None,
            )

        if isinstance(event, StandInActionDecided) or self._is_type(
            event, ["StandInActionDecided", "StandInTurnExecuted"]
        ):
            penalties = self._get_attr(event, "penalties_applied", [])
            return (
                "stand_in.turn_taken",
                {
                    "character_name": str(self._get_attr(event, "character_name", "Stand-in")),
                    "action_type": str(self._get_attr(event, "action_type", "action")),
                    "penalties_applied": list(penalties) if isinstance(penalties, list) else [],
                },
                None,
            )

        if isinstance(event, AbsencePenaltyApplied) or self._is_type(
            event, ["AbsencePenaltyApplied", "PlayerAbsenteePenalized"]
        ):
            return (
                "stand_in.penalty_applied",
                {
                    "penalty_type": str(self._get_attr(event, "penalty_type", "curse")),
                    "imposed_by": str(self._get_attr(event, "imposed_by", "the_watcher")),
                },
                None,
            )

        if isinstance(event, PlayerJoinedSession) or self._is_type(event, ["PlayerJoinedSession"]):
            pid = self._get_attr(event, "player_id")
            return (
                "player.joined",
                {
                    "session_id": sid,
                    "character_class": str(self._get_attr(event, "character_class", "unknown")),
                },
                str(pid) if pid else None,
            )

        if isinstance(event, PlayerLeftSession) or self._is_type(event, ["PlayerLeftSession"]):
            pid = self._get_attr(event, "player_id")
            return (
                "player.left",
                {"session_id": sid, "reason": str(self._get_attr(event, "reason", "disconnected"))},
                str(pid) if pid else None,
            )

        return None

    def _get_attr(self, obj: Any, key: str, default: Any = None) -> Any:
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    def _is_type(self, obj: Any, candidates: list[str]) -> bool:
        etype: str | None = None
        if isinstance(obj, dict):
            etype = str(obj.get("event_type") or obj.get("type") or "")
        elif isinstance(obj, (DomainEvent, BaseModel)):
            etype = getattr(obj, "event_type", obj.__class__.__name__)
        if not etype:
            etype = obj.__class__.__name__

        return any(
            candidate.lower() in etype.lower() or etype.lower().endswith(candidate.lower())
            for candidate in candidates
        )

    async def handle_event(self, event: Any) -> dict[str, Any] | None:
        """Map and dispatch single domain event."""
        mapped = self.map_event_to_analytics(event)
        if not mapped:
            return None
        event_name, properties, profile_id = mapped
        return await self.client.track(event_name, properties=properties, profile_id=profile_id)

    async def process_once(self, count: int = 10, block_ms: int = 200) -> int:
        """Poll each stream once, process mapped events, and acknowledge processed messages."""
        if not self.consumer_group:
            return 0

        total_processed = 0
        for stream in self.streams:
            try:
                messages = await self.consumer_group.read_group(
                    stream=stream,
                    group_name=self.group_name,
                    consumer_name=self.consumer_name,
                    count=count,
                    block_ms=block_ms,
                )
            except Exception as e:
                logger.warning("Error reading group for stream %s: %s", stream, e)
                continue

            for msg_id, event in messages:
                try:
                    await self.handle_event(event)
                    await self.consumer_group.ack(stream, self.group_name, msg_id)
                    self.processed_count += 1
                    total_processed += 1
                except Exception as exc:
                    logger.error("Failed processing analytics event %s: %s", msg_id, exc)
                    await self.consumer_group.route_to_dead_letter(
                        stream=stream,
                        message_id=str(msg_id),
                        payload=event,
                        error_reason=str(exc),
                    )
                    await self.consumer_group.ack(stream, self.group_name, msg_id)

        return total_processed

    async def start(self) -> None:
        """Start the background consumer loop."""
        await self.setup_groups()
        self.running = True
        self._task = asyncio.create_task(self._run_loop())

    async def stop(self) -> None:
        """Stop the background consumer loop."""
        self.running = False
        if self._task and not self._task.done():
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None

    async def _run_loop(self) -> None:
        while self.running:
            try:
                await self.process_once(count=self.batch_size, block_ms=self.poll_interval_ms)
            except Exception as e:
                logger.warning("Error in analytics worker loop: %s", e)
            await asyncio.sleep(0.01)


__all__ = ["AnalyticsEventWorker"]
