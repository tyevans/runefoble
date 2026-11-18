"""Voice Room Coordinator and WebRTC Audio Room Management.

Manages active audio rooms, peer memberships, duplex playback, WebRTC stream quality,
and DM moderation controls. Every room command loads the room aggregate from the event store,
saves it, and then publishes its event. No room state stays in process (TASK-0577).
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from runefoble_events.events import (
    VocalModulatorPresetAppliedEvent,
    VoiceFilterToggledEvent,
    VoicePeerJoined,
    VoicePeerLeft,
    VoicePeerMuteToggled,
)
from runefoble_platform.aggregate_loading import load_or_create
from runefoble_platform.event_publish import publish_best_effort
from runefoble_platform.event_sourcing import create_aggregate_repository
from runefoble_platform.redis_bus import RedisStreamsEventBus
from voice_agent.event_bus import get_event_bus
from voice_agent.interruption import InterruptionResult, build_interruption
from voice_agent.room_aggregate import PeerStreamState, VoiceRoomAggregate, to_uuid
from voice_agent.telemetry_view import PeerTelemetrySample, PeerTelemetryView
from voice_agent.webrtc.adaptive_bitrate import AdaptiveBitrateRegulator, OpusCodecParameters
from voice_agent.webrtc.models import RTCPReportRequest
from voice_agent.webrtc.quality_monitor import NetworkQualityMonitor, QualityMetrics

logger = logging.getLogger("runefoble.voice_agent.coordinator")
STREAM_SESSION = "runefoble.events.session"
STREAM_VOICE = "runefoble.events.voice"


@dataclass(frozen=True)
class StreamReportOutcome:
    """Result of one RTCP report: the measured quality and the codec parameters in force."""

    metrics: QualityMetrics
    codec: OpusCodecParameters
    adapted: bool
    reason: str
    previous_bitrate_kbps: int


class VoiceRoomCoordinator:
    """Coordinates active WebRTC voice rooms, peer state, playback, and stream quality."""

    def __init__(
        self,
        event_bus: RedisStreamsEventBus | None = None,
    ):
        self._event_bus = event_bus
        self._repository = create_aggregate_repository(VoiceRoomAggregate)
        self._quality = NetworkQualityMonitor()
        self._regulator = AdaptiveBitrateRegulator()
        self._telemetry = PeerTelemetryView()
        self._kick_callbacks: list[Callable[[str, str, str], Any]] = []

    def set_event_bus(self, bus: RedisStreamsEventBus | None) -> None:
        self._event_bus = bus

    def register_kick_callback(self, cb: Callable[[str, str, str], Any]) -> None:
        self._kick_callbacks.append(cb)

    async def _load_room(self, session_id: str) -> VoiceRoomAggregate:
        """Load the room from the event store on every call. No domain state stays in process."""
        return await load_or_create(self._repository, to_uuid(session_id), VoiceRoomAggregate)

    async def _commit(self, agg: VoiceRoomAggregate, event: Any) -> None:
        """Save the room before publishing its event. A failed save publishes nothing."""
        await self._repository.save(agg)
        await self._publish_event(event)

    async def peer_joined(
        self,
        session_id: str,
        peer_id: str,
        user_id: str,
        role: str = "player",
        joined_at: str | None = None,
    ) -> VoicePeerJoined:
        agg = await self._load_room(session_id)
        event = agg.join_peer(session_id, peer_id, user_id, role, joined_at)
        await self._commit(agg, event)
        return event

    async def peer_left(
        self, session_id: str, peer_id: str, reason: str = "disconnected"
    ) -> VoicePeerLeft:
        agg = await self._load_room(session_id)
        event = agg.leave_peer(session_id, peer_id, reason)
        await self._commit(agg, event)
        self._telemetry.forget(session_id, peer_id)
        return event

    async def mute_toggled(
        self, session_id: str, peer_id: str, is_muted: bool
    ) -> VoicePeerMuteToggled:
        agg = await self._load_room(session_id)
        event = agg.toggle_mute(session_id, peer_id, is_muted)
        await self._commit(agg, event)
        return event

    async def apply_vocal_preset(
        self, session_id: str, peer_id: str, preset_name: str, **kwargs: Any
    ) -> VocalModulatorPresetAppliedEvent:
        agg = await self._load_room(session_id)
        event = agg.apply_vocal_preset(session_id, peer_id, preset_name, **kwargs)
        await self._commit(agg, event)
        return event

    async def toggle_voice_filter(
        self, session_id: str, peer_id: str, filter_name: str, **kwargs: Any
    ) -> VoiceFilterToggledEvent:
        agg = await self._load_room(session_id)
        event = agg.toggle_voice_filter(session_id, peer_id, filter_name, **kwargs)
        await self._commit(agg, event)
        return event

    async def update_telemetry(
        self,
        session_id: str,
        peer_id: str,
        audio_level: float | None = None,
        latency_ms: float | None = None,
        is_speaking: bool | None = None,
    ) -> None:
        """Keep a peer's latest telemetry in the bounded view. Nothing is saved to the store.

        Telemetry from a peer that is not in the room is dropped.
        """
        agg = await self._load_room(session_id)
        if agg.state is None or peer_id not in agg.state.peers:
            return
        self._telemetry.record(
            session_id,
            peer_id,
            audio_level=audio_level,
            latency_ms=latency_ms,
            is_speaking=is_speaking,
        )

    async def get_room_summary(self, session_id: str) -> dict[str, Any]:
        agg = await self._load_room(session_id)
        peers = agg.state.peers if agg.state else {}
        samples = self._telemetry.for_session(session_id)
        participants = []
        for p in peers.values():
            item = p.model_dump()
            sample = samples.get(p.peer_id, PeerTelemetrySample())
            item.update(
                audio_level=sample.audio_level,
                latency_ms=sample.latency_ms,
                is_speaking=sample.is_speaking,
            )
            participants.append(item)
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

    async def start_playback(
        self, session_id: str, playback_id: str, text: str, duration_ms: float
    ) -> None:
        """Record that TTS narration started. The playback is kept in the room aggregate."""
        agg = await self._load_room(session_id)
        agg.start_playback(session_id, playback_id, text, duration_ms)
        await self._repository.save(agg)

    async def playback_active(self, session_id: str) -> bool:
        agg = await self._load_room(session_id)
        return agg.current_playback() is not None

    async def interrupt_playback(
        self, session_id: str, speaker_id: str, speaker_name: str, audio_tail: bytes
    ) -> InterruptionResult | None:
        """Stop the active playback on player speech. Return None when nothing is playing."""
        agg = await self._load_room(session_id)
        playback = agg.current_playback()
        if playback is None:
            return None
        result = build_interruption(
            playback, speaker_id, speaker_name, now=time.time(), audio_tail=audio_tail
        )
        agg.attenuate_playback(
            session_id,
            playback.playback_id,
            speaker_id,
            speaker_name,
            result.cutoff_position_ms,
            result.remaining_narration_text,
        )
        agg.stop_playback(session_id, playback.playback_id, reason="player_barge_in")
        await self._repository.save(agg)
        return result

    async def record_stream_report(
        self, session_id: str, user_id: str | None, report: RTCPReportRequest
    ) -> StreamReportOutcome:
        """Evaluate one RTCP report, adapt the Opus codec if needed, and save the result."""
        agg = await self._load_room(session_id)
        previous = agg.stream_codec(report.peer_id)
        metrics = self._quality.analyze_report(report.peer_id, report.model_dump())
        codec, adapted, reason = self._regulator.regulate(
            previous, metrics.packet_loss, metrics.rtt_ms
        )
        agg.measure_stream(session_id, report.peer_id, user_id, metrics)
        if adapted:
            agg.adapt_stream_codec(session_id, report.peer_id, user_id, previous, codec, reason)
        await self._repository.save(agg)
        return StreamReportOutcome(
            metrics=metrics,
            codec=codec,
            adapted=adapted,
            reason=reason,
            previous_bitrate_kbps=previous.bitrate_kbps,
        )

    async def stream_states(self, session_id: str) -> dict[str, PeerStreamState]:
        agg = await self._load_room(session_id)
        return agg.stream_states()

    async def _publish_event(self, event: Any) -> None:
        bus = self._event_bus or get_event_bus()
        for s in (STREAM_SESSION, STREAM_VOICE):
            await publish_best_effort(bus, s, event)


_default_coordinator: VoiceRoomCoordinator | None = None


def get_voice_room_coordinator() -> VoiceRoomCoordinator:
    global _default_coordinator
    if _default_coordinator is None:
        _default_coordinator = VoiceRoomCoordinator()
    return _default_coordinator


def set_voice_room_coordinator(coordinator: VoiceRoomCoordinator | None) -> None:
    global _default_coordinator
    _default_coordinator = coordinator
