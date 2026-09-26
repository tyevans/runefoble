"""Voice Room Coordinator and WebRTC Audio Room Management.

Manages active audio rooms, peer memberships, WebRTC session telemetry,
and DM moderation controls.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from runefoble_auth.spicedb import SpiceDBClient
from runefoble_events.voice import VoicePeerJoined, VoicePeerLeft, VoicePeerMuteToggled
from runefoble_platform.event_sourcing import create_aggregate_repository
from runefoble_platform.redis_bus import RedisStreamsEventBus
from voice_agent.room_aggregate import VoiceRoomAggregate, to_uuid

logger = logging.getLogger("runefoble.voice_agent.coordinator")
STREAM_SESSION = "runefoble.events.session"
STREAM_VOICE = "runefoble.events.voice"


class VoiceRoomCoordinator:
    """Coordinates active WebRTC voice rooms, peer state, and telemetry across sessions."""

    def __init__(
        self,
        event_bus: RedisStreamsEventBus | None = None,
        spicedb_client: SpiceDBClient | None = None,
    ):
        self._event_bus = event_bus
        self._spicedb = spicedb_client
        self._repository = create_aggregate_repository(VoiceRoomAggregate)
        self._telemetry: dict[str, dict[str, dict[str, Any]]] = {}
        self._aggregates: dict[str, VoiceRoomAggregate] = {}
        self._kick_callbacks: list[Callable[[str, str, str], Any]] = []

    @property
    def spicedb(self) -> SpiceDBClient:
        if self._spicedb is None:
            self._spicedb = SpiceDBClient()
        return self._spicedb

    def set_spicedb(self, client: SpiceDBClient) -> None:
        self._spicedb = client

    def set_event_bus(self, bus: RedisStreamsEventBus | None) -> None:
        self._event_bus = bus

    def register_kick_callback(self, cb: Callable[[str, str, str], Any]) -> None:
        self._kick_callbacks.append(cb)

    async def get_or_load_room(self, session_id: str) -> VoiceRoomAggregate:
        if session_id in self._aggregates:
            return self._aggregates[session_id]
        room_uuid = to_uuid(session_id)
        try:
            agg = await self._repository.load(room_uuid)
        except Exception:
            agg = VoiceRoomAggregate(room_uuid)
        self._aggregates[session_id] = agg
        return agg

    async def peer_joined(
        self,
        session_id: str,
        peer_id: str,
        user_id: str,
        role: str = "player",
        joined_at: str | None = None,
    ) -> VoicePeerJoined:
        agg = await self.get_or_load_room(session_id)
        event = agg.join_peer(session_id, peer_id, user_id, role, joined_at)
        await self._publish_event(event)
        return event

    async def peer_left(
        self, session_id: str, peer_id: str, reason: str = "disconnected"
    ) -> VoicePeerLeft:
        agg = await self.get_or_load_room(session_id)
        event = agg.leave_peer(session_id, peer_id, reason)
        await self._publish_event(event)
        if session_id in self._telemetry:
            self._telemetry[session_id].pop(peer_id, None)
        return event

    async def mute_toggled(
        self, session_id: str, peer_id: str, is_muted: bool
    ) -> VoicePeerMuteToggled:
        agg = await self.get_or_load_room(session_id)
        event = agg.toggle_mute(session_id, peer_id, is_muted)
        await self._publish_event(event)
        return event

    def update_telemetry(
        self,
        session_id: str,
        peer_id: str,
        audio_level: float | None = None,
        latency_ms: float | None = None,
        is_speaking: bool | None = None,
    ) -> None:
        t = self._telemetry.setdefault(session_id, {}).setdefault(peer_id, {})
        if audio_level is not None:
            t["audio_level"] = audio_level
        if latency_ms is not None:
            t["latency_ms"] = latency_ms
        if is_speaking is not None:
            t["is_speaking"] = is_speaking

    async def get_room_summary(self, session_id: str) -> dict[str, Any]:
        agg = await self.get_or_load_room(session_id)
        peers = agg.state.peers if agg.state else {}
        room_t = self._telemetry.get(session_id, {})
        participants = [
            {
                "peer_id": p.peer_id,
                "user_id": p.user_id,
                "role": p.role,
                "joined_at": p.joined_at,
                "is_muted": p.is_muted,
                "audio_level": room_t.get(pid, {}).get("audio_level", p.audio_level),
                "latency_ms": room_t.get(pid, {}).get("latency_ms", p.latency_ms),
                "is_speaking": room_t.get(pid, {}).get("is_speaking", p.is_speaking),
            }
            for pid, p in peers.items()
        ]
        return {
            "session_id": session_id,
            "active": True,
            "participant_count": len(participants),
            "participants": participants,
        }

    async def kick_peer(
        self, session_id: str, peer_id: str, kicked_by: str, reason: str = "kicked_by_dm"
    ) -> dict[str, Any]:
        await self.peer_left(session_id, peer_id, reason=reason)
        for cb in self._kick_callbacks:
            try:
                res = cb(session_id, peer_id, reason)
                if hasattr(res, "__await__"):
                    await res
            except Exception as e:
                logger.warning("Error in kick callback: %s", e)
        return {
            "status": "kicked",
            "session_id": session_id,
            "peer_id": peer_id,
            "reason": reason,
            "kicked_by": kicked_by,
        }

    async def _publish_event(self, event: Any) -> None:
        bus = self._event_bus
        if bus is None:
            for mod_name, attr in [
                ("gateway_api.main", "get_event_bus"),
                ("voice_agent.main", "_event_bus"),
            ]:
                try:
                    mod = __import__(mod_name, fromlist=[attr])
                    val = getattr(mod, attr, None)
                    bus = val() if callable(val) else val
                    if bus:
                        break
                except Exception:
                    continue
        if bus is not None:
            for stream in (STREAM_SESSION, STREAM_VOICE):
                try:
                    await bus.publish_event(stream, event)
                except Exception as e:
                    logger.warning(
                        "Failed to publish %s to %s: %s", type(event).__name__, stream, e
                    )


_default_coordinator: VoiceRoomCoordinator | None = None


def get_voice_room_coordinator() -> VoiceRoomCoordinator:
    global _default_coordinator
    if _default_coordinator is None:
        _default_coordinator = VoiceRoomCoordinator()
    return _default_coordinator


def set_voice_room_coordinator(coordinator: VoiceRoomCoordinator | None) -> None:
    global _default_coordinator
    _default_coordinator = coordinator
