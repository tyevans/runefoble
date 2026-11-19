"""Shared dependencies, runtime state, and event dispatchers for Voice Agent."""

from __future__ import annotations

import logging
from typing import Any

from runefoble_auth.settings import load_spicedb_settings
from runefoble_platform.event_publish import publish_best_effort
from runefoble_platform.redis_bus import RedisStreamsEventBus
from voice_agent.dsp import VoiceDSPPipeline
from voice_agent.event_bus import get_event_bus, set_event_bus

logger = logging.getLogger("runefoble.voice_agent")
STREAM_SESSION = "runefoble.events.session"
STREAM_VOICE = "runefoble.events.voice"

# This service checks SpiceDB permissions. Fail fast at start-up without the key (TASK-0720).
load_spicedb_settings()
dsp_pipeline = VoiceDSPPipeline()


async def publish_voice_event(event: Any, bus: RedisStreamsEventBus | None = None) -> None:
    """Publish a notification event to session and voice Redis Streams (best effort, counted)."""
    active_bus = bus or get_event_bus()
    for stream in (STREAM_SESSION, STREAM_VOICE):
        await publish_best_effort(active_bus, stream, event)


__all__ = [
    "STREAM_SESSION",
    "STREAM_VOICE",
    "dsp_pipeline",
    "get_event_bus",
    "logger",
    "publish_voice_event",
    "set_event_bus",
]
