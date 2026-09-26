"""OpenPanel Privacy-Preserving Analytics SDK & Redis Streams Consumer Worker.

Provides privacy-first event tracking without storing raw audio, voice transcripts,
or unhashed personally identifiable information (PII).
"""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import logging
from typing import Any
from uuid import UUID

import httpx
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

from runefoble_platform.config import PlatformSettings
from runefoble_platform.consumer_group import RedisConsumerGroup

logger = logging.getLogger(__name__)

FORBIDDEN_PROPERTY_KEYS = {
    "transcript",
    "raw_transcript",
    "audio",
    "raw_audio",
    "speech",
    "dialogue",
    "password",
    "token",
    "secret",
    "email",
}


def anonymize_profile_id(
    profile_id: str | UUID | None, salt: str = "runefoble_privacy_salt"
) -> str | None:
    """Hash profile identifiers using salted SHA-256 to ensure player privacy."""
    if not profile_id:
        return None
    raw = str(profile_id).strip()
    if not raw:
        return None
    hasher = hashlib.sha256(f"{salt}:{raw}".encode())
    return hasher.hexdigest()[:32]


def sanitize_properties(properties: dict[str, Any] | None) -> dict[str, Any]:
    """Recursively scrub forbidden PII, audio bytes, and speech transcripts from properties."""
    if not properties:
        return {}
    sanitized: dict[str, Any] = {}
    for key, val in properties.items():
        lower_key = str(key).lower()
        if (
            lower_key in FORBIDDEN_PROPERTY_KEYS
            or "audio" in lower_key
            or "transcript" in lower_key
        ):
            continue
        if isinstance(val, dict):
            sanitized[key] = sanitize_properties(val)
        elif isinstance(val, (list, tuple)):
            sanitized[key] = [
                sanitize_properties(v) if isinstance(v, dict) else v
                for v in val
                if not (isinstance(v, str) and len(v) > 2048)
            ]
        elif isinstance(val, (UUID,)):
            sanitized[key] = str(val)
        else:
            sanitized[key] = val
    return sanitized


class OpenPanelClient:
    """Privacy-preserving OpenPanel client supporting non-blocking HTTP dispatch and mock recording."""

    def __init__(
        self,
        endpoint: str | None = None,
        client_id: str | None = None,
        salt: str = "runefoble_privacy_salt",
        mock_mode: bool = False,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        settings = PlatformSettings()
        raw_endpoint = endpoint or settings.openpanel_endpoint
        self.endpoint = raw_endpoint.rstrip("/") if raw_endpoint else "http://localhost:3000/api"
        self.client_id = client_id or settings.openpanel_client_id
        self.salt = salt
        self.mock_mode = mock_mode
        self._http_client = http_client
        self.recorded_events: list[dict[str, Any]] = []

    async def _get_client(self) -> httpx.AsyncClient:
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=3.0)
        return self._http_client

    async def track(
        self,
        event_name: str,
        properties: dict[str, Any] | None = None,
        profile_id: str | UUID | None = None,
    ) -> dict[str, Any]:
        """Record an anonymized event and dispatch asynchronously to OpenPanel."""
        anon_profile = anonymize_profile_id(profile_id, salt=self.salt)
        clean_props = sanitize_properties(properties)

        payload: dict[str, Any] = {
            "event": event_name,
            "name": event_name,
            "properties": clean_props,
        }
        if anon_profile:
            payload["profile_id"] = anon_profile
        if self.client_id:
            payload["client_id"] = self.client_id

        self.recorded_events.append(payload)

        if not self.mock_mode and self.endpoint:
            url = f"{self.endpoint}/event"
            headers = {"Content-Type": "application/json"}
            if self.client_id:
                headers["openpanel-client-id"] = self.client_id
            try:
                client = await self._get_client()
                await client.post(url, json=payload, headers=headers)
            except Exception as exc:
                logger.warning("OpenPanel async dispatch failed for '%s': %s", event_name, exc)

        return payload

    async def identify(
        self,
        profile_id: str | UUID,
        traits: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Record an anonymized profile identifier with privacy-sanitized traits."""
        anon_profile = anonymize_profile_id(profile_id, salt=self.salt)
        clean_traits = sanitize_properties(traits)
        payload: dict[str, Any] = {
            "profile_id": anon_profile,
            "traits": clean_traits,
        }
        if self.client_id:
            payload["client_id"] = self.client_id

        self.recorded_events.append(payload)

        if not self.mock_mode and self.endpoint:
            url = f"{self.endpoint}/profile"
            headers = {"Content-Type": "application/json"}
            if self.client_id:
                headers["openpanel-client-id"] = self.client_id
            try:
                client = await self._get_client()
                await client.post(url, json=payload, headers=headers)
            except Exception as exc:
                logger.warning("OpenPanel profile dispatch failed: %s", exc)

        return payload

    def clear(self) -> None:
        """Clear recorded events from memory buffer."""
        self.recorded_events.clear()

    async def close(self) -> None:
        """Close internal HTTP client session."""
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()


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


__all__ = [
    "FORBIDDEN_PROPERTY_KEYS",
    "anonymize_profile_id",
    "sanitize_properties",
    "OpenPanelClient",
    "AnalyticsEventWorker",
]
