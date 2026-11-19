"""Shared dependencies, runtime state, and event dispatchers for Voice Agent."""

from __future__ import annotations

import logging
from typing import Any

import httpx
from runefoble_auth.settings import load_spicedb_settings
from runefoble_platform.config import PlatformSettings
from runefoble_platform.event_publish import publish_best_effort
from runefoble_platform.redis_bus import RedisStreamsEventBus
from voice_agent.dsp import VoiceDSPPipeline
from voice_agent.event_bus import get_event_bus, set_event_bus
from voice_agent.stt import get_streaming_pipeline

logger = logging.getLogger("runefoble.voice_agent")
STREAM_SESSION = "runefoble.events.session"
STREAM_VOICE = "runefoble.events.voice"

platform_settings = PlatformSettings()
# This service checks SpiceDB permissions. Fail fast at start-up without the key (TASK-0720).
load_spicedb_settings()
dsp_pipeline = VoiceDSPPipeline()


def set_watcher_client(client: httpx.AsyncClient | None) -> None:
    get_streaming_pipeline().set_watcher_client(client)


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
    "platform_settings",
    "publish_voice_event",
    "set_event_bus",
    "set_watcher_client",
]
