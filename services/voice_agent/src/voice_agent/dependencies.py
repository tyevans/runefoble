"""Shared dependencies, runtime state, and event dispatchers for Voice Agent."""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx
from runefoble_events.events import VoiceAudioConditioned
from runefoble_platform.config import PlatformSettings
from runefoble_platform.redis_bus import RedisStreamsEventBus
from voice_agent.dsp import VoiceDSPPipeline
from voice_agent.room import get_voice_room_coordinator
from voice_agent.room_aggregate import to_uuid
from voice_agent.stt import get_streaming_pipeline

logger = logging.getLogger("runefoble.voice_agent")
WATCHER_URL = os.environ.get("RUNEFOBLE_WATCHER_URL", "http://localhost:8001")
STREAM_SESSION = "runefoble.events.session"
STREAM_VOICE = "runefoble.events.voice"

platform_settings = PlatformSettings()
_event_bus: RedisStreamsEventBus | None = None
dsp_pipeline = VoiceDSPPipeline()


def get_event_bus() -> RedisStreamsEventBus:
    global _event_bus
    if _event_bus is None:
        _event_bus = RedisStreamsEventBus(redis_url=platform_settings.redis_url)
    return _event_bus


def set_event_bus(bus: RedisStreamsEventBus | None) -> None:
    global _event_bus
    _event_bus = bus
    get_voice_room_coordinator().set_event_bus(bus)
    get_streaming_pipeline().set_event_bus(bus)


def set_watcher_client(client: httpx.AsyncClient | None) -> None:
    get_streaming_pipeline().set_watcher_client(client)


async def _dispatch_voice_audio_conditioned(
    session_id: str,
    speaker_id: str,
    speaker_name: str,
    filters_applied: list[str],
    latency_ms: float,
    audio_bytes_length: int,
) -> None:
    """Publish VoiceAudioConditioned domain event to session and voice event streams."""
    event = VoiceAudioConditioned(
        session_id=session_id,
        speaker_id=speaker_id,
        speaker_name=speaker_name,
        filters_applied=filters_applied,
        latency_ms=latency_ms,
        audio_bytes_length=audio_bytes_length,
    )
    bus = get_event_bus()
    for stream in (STREAM_SESSION, STREAM_VOICE):
        try:
            await bus.publish_event(stream, event)
        except Exception as e:
            logger.warning("Failed to publish VoiceAudioConditioned to '%s': %s", stream, e)


async def publish_voice_event(event: Any, bus: RedisStreamsEventBus | None = None) -> None:
    """Publish a domain event to session and voice Redis Streams."""
    active_bus = bus or get_event_bus()
    if active_bus:
        for stream in (STREAM_SESSION, STREAM_VOICE):
            try:
                await active_bus.publish_event(stream, event)
            except Exception as e:
                logger.warning("Failed to publish %s to %s: %s", type(event).__name__, stream, e)


__all__ = [
    "STREAM_SESSION",
    "STREAM_VOICE",
    "WATCHER_URL",
    "_dispatch_voice_audio_conditioned",
    "dsp_pipeline",
    "get_event_bus",
    "logger",
    "platform_settings",
    "publish_voice_event",
    "set_event_bus",
    "set_watcher_client",
    "to_uuid",
]
