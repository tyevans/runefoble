"""Shared dependency injection, repositories, mixer, and event bus for Soundscape."""

from __future__ import annotations

import contextlib
import logging
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import Header
from runefoble_auth.spicedb import MockSpiceDBClient, SpiceDBClient
from runefoble_events.base import BaseRunefobleEvent
from runefoble_platform.bus import bus as platform_bus
from runefoble_platform.config import PlatformSettings
from runefoble_platform.event_sourcing import AggregateRepository, create_aggregate_repository
from runefoble_platform.redis_bus import RedisStreamsEventBus

from soundscape.aggregate import SoundscapeAggregate
from soundscape.event_handlers import (
    handle_incoming_domain_event,
    register_soundscape_event_handlers,
)

__all__ = ["handle_incoming_domain_event", "register_soundscape_event_handlers"]
from soundscape.leitmotif import LeitmotifEngine
from soundscape.mixer import AudioStemMixer

logger = logging.getLogger("runefoble.soundscape")
settings = PlatformSettings()

_event_bus: RedisStreamsEventBus | None = None
_soundscape_repo = create_aggregate_repository(SoundscapeAggregate)
_spicedb_client: SpiceDBClient | MockSpiceDBClient | None = None

_session_to_aggregate: dict[str, UUID] = {}
_session_mixers: dict[str, AudioStemMixer] = {}
_session_leitmotif_engines: dict[str, LeitmotifEngine] = {}


def get_soundscape_repo() -> AggregateRepository[SoundscapeAggregate]:
    """Provide SoundscapeAggregate repository singleton."""
    return _soundscape_repo


def get_spicedb_client() -> SpiceDBClient | MockSpiceDBClient:
    """Provide SpiceDB Zanzibar authorization client."""
    global _spicedb_client
    if _spicedb_client is None:
        _spicedb_client = SpiceDBClient(
            endpoint=settings.spicedb_endpoint or "localhost:50051",
            token=getattr(settings, "spicedb_token", "secret"),
        )
    return _spicedb_client


def set_spicedb_client(client: SpiceDBClient | MockSpiceDBClient | None) -> None:
    """Override SpiceDB client for testing."""
    global _spicedb_client
    _spicedb_client = client


def get_event_bus() -> RedisStreamsEventBus | None:
    """Provide RedisStreamsEventBus instance."""
    global _event_bus
    if _event_bus is None and settings.redis_url:
        with contextlib.suppress(Exception):
            _event_bus = RedisStreamsEventBus(redis_url=settings.redis_url)
    return _event_bus


def set_event_bus(bus: RedisStreamsEventBus | None) -> None:
    """Override event bus for testing."""
    global _event_bus
    _event_bus = bus


def get_or_create_aggregate_id(session_id: str) -> UUID:
    """Resolve or generate UUID for a session's soundscape aggregate."""
    if session_id not in _session_to_aggregate:
        _session_to_aggregate[session_id] = uuid4()
    return _session_to_aggregate[session_id]


def get_or_create_mixer(session_id: str) -> AudioStemMixer:
    """Resolve or instantiate AudioStemMixer for a session."""
    if session_id not in _session_mixers:
        _session_mixers[session_id] = AudioStemMixer(stem_profile="exploration", master_volume=1.0)
    return _session_mixers[session_id]


def get_or_create_leitmotif_engine(session_id: str) -> LeitmotifEngine:
    """Resolve or instantiate LeitmotifEngine for a session."""
    if session_id not in _session_leitmotif_engines:
        _session_leitmotif_engines[session_id] = LeitmotifEngine(session_id=session_id)
    return _session_leitmotif_engines[session_id]


def reset_dependencies() -> None:
    """Clear in-memory session registries and reset mocks."""
    global _event_bus
    _session_to_aggregate.clear()
    _session_mixers.clear()
    _session_leitmotif_engines.clear()
    _event_bus = None


def get_current_user_id(
    x_user_id: Annotated[str | None, Header(alias="x-user-id")] = None,
) -> str | None:
    """Extract authenticated caller identity from x-user-id header."""
    return x_user_id


async def check_user_can_control_soundscape(
    user_id: str | None,
    session_id: str,
    campaign_id: UUID | None,
    spicedb: SpiceDBClient,
) -> bool:
    """Check Zanzibar authorization for managing audio soundscapes."""
    if not user_id:
        return True
    with contextlib.suppress(Exception):
        if await spicedb.check_permission("session", session_id, "control", "user", user_id):
            return True
    if campaign_id:
        with contextlib.suppress(Exception):
            cid = str(campaign_id)
            for perm in ("run_session", "play"):
                if await spicedb.check_permission("campaign", cid, perm, "user", user_id):
                    return True
    return False


async def publish_soundscape_event(event: BaseRunefobleEvent) -> None:
    """Publish soundscape domain event across in-memory platform bus and Redis Streams."""
    with contextlib.suppress(Exception):
        await platform_bus.publish(event.event_type, event)
    bus = get_event_bus()
    if bus:
        with contextlib.suppress(Exception):
            await bus.publish_event("runefoble.events.soundscape", event)
