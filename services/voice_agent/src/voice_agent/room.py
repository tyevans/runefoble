"""Voice Room Coordinator and WebRTC Audio Room Management.

Re-exports room aggregates, state models, and coordinator for backward compatibility.
"""

from __future__ import annotations

from voice_agent.coordinator import (
    STREAM_SESSION,
    STREAM_VOICE,
    VoiceRoomCoordinator,
    get_voice_room_coordinator,
    set_voice_room_coordinator,
)
from voice_agent.room_aggregate import (
    VoicePeerState,
    VoiceRoomAggregate,
    VoiceRoomState,
    to_uuid,
)

__all__ = [
    "STREAM_SESSION",
    "STREAM_VOICE",
    "VoicePeerState",
    "VoiceRoomAggregate",
    "VoiceRoomCoordinator",
    "VoiceRoomState",
    "get_voice_room_coordinator",
    "set_voice_room_coordinator",
    "to_uuid",
]
