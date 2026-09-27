"""Voice Room Aggregate and Peer State Models.

Event-sourced aggregate managing WebRTC voice room peers and audio states (Hard Invariant 2).
"""

from __future__ import annotations

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
    audio_level: float = 0.0
    latency_ms: float = 0.0
    is_speaking: bool = False
    active_preset: str | None = None
    pitch_shift_semitones: float = 0.0
    formant_shift: float = 1.0
    resonance_hz: float = 0.0
    dsp_filters: list[str] = Field(default_factory=list)


class VoiceRoomState(BaseModel):
    session_id: str
    peers: dict[str, VoicePeerState] = Field(default_factory=dict)
    active: bool = True


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

    @handles(VoicePeerJoined)
    def _on_peer_joined(self, event: VoicePeerJoined) -> None:
        if self._state is None:
            self._state = VoiceRoomState(session_id=event.session_id, peers={})
        peers = dict(self.state.peers)
        peers[event.peer_id] = VoicePeerState(
            peer_id=event.peer_id,
            user_id=event.user_id,
            role=event.role,
            joined_at=event.joined_at,
            is_muted=False,
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
