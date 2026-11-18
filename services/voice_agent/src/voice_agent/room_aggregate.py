"""Voice Room Aggregate and Peer State Models.

Event-sourced aggregate managing WebRTC voice room peers and audio states (Hard Invariant 2).
"""

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Any
from uuid import NAMESPACE_DNS, UUID, uuid4, uuid5

from eventsource.domain.aggregate import DeclarativeAggregate
from eventsource.domain.decorators import handles
from pydantic import BaseModel, Field
from runefoble_events.vocal_dsp import (
    VocalModulatorPresetAppliedEvent,
    VoiceFilterToggledEvent,
)
from runefoble_events.voice import (
    VoicePeerJoined,
    VoicePeerLeft,
    VoicePeerMuteToggled,
)
from runefoble_events.voice_playback import (
    VoicePlaybackAttenuated,
    VoicePlaybackStarted,
    VoicePlaybackStopped,
)
from runefoble_events.voice_stream_quality import (
    VoiceStreamCodecAdaptedEvent,
    VoiceStreamQualityMeasured,
)
from voice_agent.webrtc.adaptive_bitrate import TIER_PROFILES, OpusCodecParameters
from voice_agent.webrtc.quality_monitor import QualityMetrics


def to_uuid(val: str | UUID | None) -> UUID:
    """Deterministically convert string or UUID into a valid UUID."""
    if val is None:
        return uuid4()
    if isinstance(val, UUID):
        return val
    try:
        return UUID(val)
    except ValueError:
        return uuid5(NAMESPACE_DNS, str(val))


class VoicePeerState(BaseModel):
    peer_id: str
    user_id: str
    role: str = "player"
    joined_at: str
    is_muted: bool = False
    active_preset: str | None = None
    pitch_shift_semitones: float = 0.0
    formant_shift: float = 1.0
    resonance_hz: float = 0.0
    dsp_filters: list[str] = Field(default_factory=list)


class VoicePlaybackState(BaseModel):
    """TTS narration that is playing in the room. Cleared by a playback stop event."""

    session_id: str
    playback_id: str
    original_text: str
    duration_ms: float
    started_at: float


class PeerStreamState(BaseModel):
    """Latest RTCP quality measurement and Opus codec parameters for one peer."""

    packet_loss: float = 0.0
    rtt_ms: float = 0.0
    jitter_ms: float = 0.0
    is_degraded: bool = False
    severity: str = "nominal"
    detection_latency_ms: float = 0.0
    codec: OpusCodecParameters = Field(
        default_factory=lambda: TIER_PROFILES["standard"].model_copy()
    )


class VoiceRoomState(BaseModel):
    session_id: str
    peers: dict[str, VoicePeerState] = Field(default_factory=dict)
    active: bool = True
    playback: VoicePlaybackState | None = None
    streams: dict[str, PeerStreamState] = Field(default_factory=dict)


class VoiceRoomAggregate(DeclarativeAggregate[VoiceRoomState]):
    """Event-sourced aggregate managing WebRTC voice room peers and audio states."""

    aggregate_type = "VoiceRoom"
    requires_creation_event = False

    def join_peer(
        self,
        session_id: str,
        peer_id: str,
        user_id: str,
        role: str = "player",
        joined_at: str | None = None,
    ) -> VoicePeerJoined:
        joined_time = joined_at or datetime.now(UTC).isoformat()
        return self.create_event(
            VoicePeerJoined,
            session_id=session_id,
            peer_id=peer_id,
            user_id=user_id,
            role=role,
            joined_at=joined_time,
        )

    def leave_peer(
        self, session_id: str, peer_id: str, reason: str = "disconnected"
    ) -> VoicePeerLeft:
        return self.create_event(
            VoicePeerLeft, session_id=session_id, peer_id=peer_id, reason=reason
        )

    def toggle_mute(self, session_id: str, peer_id: str, is_muted: bool) -> VoicePeerMuteToggled:
        return self.create_event(
            VoicePeerMuteToggled, session_id=session_id, peer_id=peer_id, is_muted=is_muted
        )

    def apply_vocal_preset(
        self, session_id: str, peer_id: str, preset_name: str, **kwargs: Any
    ) -> VocalModulatorPresetAppliedEvent:
        return self.create_event(
            VocalModulatorPresetAppliedEvent,
            session_id=session_id,
            peer_id=peer_id,
            preset_name=preset_name,
            **kwargs,
        )

    def toggle_voice_filter(
        self, session_id: str, peer_id: str, filter_name: str, **kwargs: Any
    ) -> VoiceFilterToggledEvent:
        return self.create_event(
            VoiceFilterToggledEvent,
            session_id=session_id,
            peer_id=peer_id,
            filter_name=filter_name,
            **kwargs,
        )

    def start_playback(
        self, session_id: str, playback_id: str, original_text: str, duration_ms: float
    ) -> VoicePlaybackStarted:
        return self.create_event(
            VoicePlaybackStarted,
            session_id=session_id,
            playback_id=playback_id,
            original_text=original_text,
            duration_ms=duration_ms,
            started_at=time.time(),
        )

    def attenuate_playback(
        self,
        session_id: str,
        playback_id: str,
        speaker_id: str,
        speaker_name: str,
        cutoff_position_ms: float,
        remaining_narration_text: str,
    ) -> VoicePlaybackAttenuated:
        return self.create_event(
            VoicePlaybackAttenuated,
            session_id=session_id,
            playback_id=playback_id,
            speaker_id=speaker_id,
            speaker_name=speaker_name,
            cutoff_position_ms=cutoff_position_ms,
            remaining_narration_text=remaining_narration_text,
        )

    def stop_playback(
        self, session_id: str, playback_id: str, reason: str = "player_barge_in"
    ) -> VoicePlaybackStopped:
        return self.create_event(
            VoicePlaybackStopped, session_id=session_id, playback_id=playback_id, reason=reason
        )

    def measure_stream(
        self, session_id: str, peer_id: str, user_id: str | None, metrics: QualityMetrics
    ) -> VoiceStreamQualityMeasured:
        return self.create_event(
            VoiceStreamQualityMeasured,
            session_id=session_id,
            peer_id=peer_id,
            user_id=user_id,
            packet_loss=metrics.packet_loss,
            rtt_ms=metrics.rtt_ms,
            jitter_ms=metrics.jitter_ms,
            is_degraded=metrics.is_degraded,
            severity=metrics.severity,
            detection_latency_ms=metrics.detection_latency_ms,
        )

    def adapt_stream_codec(
        self,
        session_id: str,
        peer_id: str,
        user_id: str | None,
        previous: OpusCodecParameters,
        current: OpusCodecParameters,
        reason: str,
    ) -> VoiceStreamCodecAdaptedEvent:
        return self.create_event(
            VoiceStreamCodecAdaptedEvent,
            session_id=session_id,
            peer_id=peer_id,
            user_id=user_id,
            previous_bitrate_kbps=previous.bitrate_kbps,
            new_bitrate_kbps=current.bitrate_kbps,
            sample_rate=current.sample_rate,
            channels=current.channels,
            complexity=current.complexity,
            fec_enabled=current.fec_enabled,
            dtx_enabled=current.dtx_enabled,
            codec_mode=current.codec_mode,
            reason=reason,
        )

    def current_playback(self) -> VoicePlaybackState | None:
        return self._state.playback if self._state else None

    def stream_states(self) -> dict[str, PeerStreamState]:
        return self._streams()

    def stream_codec(self, peer_id: str) -> OpusCodecParameters:
        """Current Opus parameters for a peer. The standard profile applies until it adapts."""
        stream = self._state.streams.get(peer_id) if self._state else None
        return stream.codec if stream else TIER_PROFILES["standard"].model_copy()

    def _stream_for(self, peer_id: str) -> PeerStreamState:
        stream = self._state.streams.get(peer_id) if self._state else None
        return stream or PeerStreamState()

    def _with_state(self, session_id: str, **updates: Any) -> None:
        base = self._state or VoiceRoomState(session_id=session_id, peers={})
        self._state = base.model_copy(update=updates)

    @handles(VoicePlaybackStarted)
    def _on_playback_started(self, event: VoicePlaybackStarted) -> None:
        playback = VoicePlaybackState(
            session_id=event.session_id,
            playback_id=event.playback_id,
            original_text=event.original_text,
            duration_ms=event.duration_ms,
            started_at=event.started_at,
        )
        self._with_state(event.session_id, playback=playback)

    @handles(VoicePlaybackAttenuated)
    def _on_playback_attenuated(self, event: VoicePlaybackAttenuated) -> None:
        """Record only. The playback ends with the stop event that follows it."""

    @handles(VoicePlaybackStopped)
    def _on_playback_stopped(self, event: VoicePlaybackStopped) -> None:
        playback = self.current_playback()
        if playback is not None and playback.playback_id == event.playback_id:
            self._state = self.state.model_copy(update={"playback": None})

    @handles(VoiceStreamQualityMeasured)
    def _on_stream_measured(self, event: VoiceStreamQualityMeasured) -> None:
        stream = self._stream_for(event.peer_id).model_copy(
            update={
                "packet_loss": event.packet_loss,
                "rtt_ms": event.rtt_ms,
                "jitter_ms": event.jitter_ms,
                "is_degraded": event.is_degraded,
                "severity": event.severity,
                "detection_latency_ms": event.detection_latency_ms,
            }
        )
        self._with_state(event.session_id, streams={**self._streams(), event.peer_id: stream})

    @handles(VoiceStreamCodecAdaptedEvent)
    def _on_codec_adapted(self, event: VoiceStreamCodecAdaptedEvent) -> None:
        codec = OpusCodecParameters(
            sample_rate=event.sample_rate,
            channels=event.channels,
            bitrate_kbps=event.new_bitrate_kbps,
            complexity=event.complexity,
            fec_enabled=event.fec_enabled,
            dtx_enabled=event.dtx_enabled,
            codec_mode=event.codec_mode,
        )
        stream = self._stream_for(event.peer_id).model_copy(update={"codec": codec})
        self._with_state(event.session_id, streams={**self._streams(), event.peer_id: stream})

    def _streams(self) -> dict[str, PeerStreamState]:
        return dict(self._state.streams) if self._state else {}

    @handles(VoicePeerJoined)
    def _on_peer_joined(self, event: VoicePeerJoined) -> None:
        if self._state is None:
            self._state = VoiceRoomState(session_id=event.session_id, peers={})
        peers = dict(self.state.peers)
        existing = peers.get(event.peer_id)
        # A rejoin keeps the seat's settings (mute, vocal preset, filters) and refreshes identity.
        peers[event.peer_id] = (
            existing.model_copy(
                update={
                    "user_id": event.user_id,
                    "role": event.role,
                    "joined_at": event.joined_at,
                }
            )
            if existing
            else VoicePeerState(
                peer_id=event.peer_id,
                user_id=event.user_id,
                role=event.role,
                joined_at=event.joined_at,
                is_muted=False,
            )
        )
        self._state = self.state.model_copy(update={"peers": peers})

    @handles(VoicePeerLeft)
    def _on_peer_left(self, event: VoicePeerLeft) -> None:
        if self._state is not None:
            peers = dict(self.state.peers)
            peers.pop(event.peer_id, None)
            self._state = self.state.model_copy(update={"peers": peers})

    @handles(VoicePeerMuteToggled)
    def _on_mute_toggled(self, event: VoicePeerMuteToggled) -> None:
        if self._state and event.peer_id in self.state.peers:
            peers = dict(self.state.peers)
            curr = peers[event.peer_id]
            peers[event.peer_id] = curr.model_copy(update={"is_muted": event.is_muted})
            self._state = self.state.model_copy(update={"peers": peers})

    @handles(VocalModulatorPresetAppliedEvent)
    def _on_preset_applied(self, event: VocalModulatorPresetAppliedEvent) -> None:
        if self._state is None:
            self._state = VoiceRoomState(session_id=event.session_id, peers={})
        peers = dict(self.state.peers)
        curr = peers.get(event.peer_id)
        updates = {
            "active_preset": event.preset_name,
            "pitch_shift_semitones": event.pitch_shift_semitones,
            "formant_shift": event.formant_shift,
            "resonance_hz": event.resonance_hz,
            "dsp_filters": list(event.active_filters),
        }
        peers[event.peer_id] = (
            curr.model_copy(update=updates)
            if curr
            else VoicePeerState(
                peer_id=event.peer_id, user_id=event.user_id, joined_at="", **updates
            )
        )
        self._state = self.state.model_copy(update={"peers": peers})

    @handles(VoiceFilterToggledEvent)
    def _on_filter_toggled(self, event: VoiceFilterToggledEvent) -> None:
        if self._state and event.peer_id in self.state.peers:
            peers = dict(self.state.peers)
            curr = peers[event.peer_id]
            filters = [f for f in curr.dsp_filters if f != event.filter_name]
            if event.enabled:
                filters.append(event.filter_name)
            peers[event.peer_id] = curr.model_copy(update={"dsp_filters": filters})
            self._state = self.state.model_copy(update={"peers": peers})
