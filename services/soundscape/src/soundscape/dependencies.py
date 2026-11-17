"""Shared dependency injection, repositories, mixer, and event bus for Soundscape."""

from __future__ import annotations

import contextlib
import logging
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import Depends
from runefoble_auth.principal import VerifiedPrincipal, require_principal
from runefoble_auth.spicedb import MockSpiceDBClient, SpiceDBClient
from runefoble_auth.zitadel import ZitadelAuthService
from runefoble_events.base import BaseRunefobleEvent
from runefoble_platform.bus import bus as platform_bus
from runefoble_platform.config import PlatformSettings
from runefoble_platform.event_publish import deliver_best_effort, publish_best_effort
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
_zitadel_auth_service: ZitadelAuthService | None = None


def get_soundscape_repo() -> AggregateRepository[SoundscapeAggregate]:
    """Provide SoundscapeAggregate repository singleton."""
    return _soundscape_repo


def get_spicedb_client() -> SpiceDBClient | MockSpiceDBClient:
    """Provide SpiceDB Zanzibar authorization client."""
    global _spicedb_client
    if _spicedb_client is None:
        _spicedb_client = SpiceDBClient(
            endpoint=settings.spicedb_endpoint or "localhost:50051",
            token=settings.spicedb_preshared_key,
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


def get_zitadel_auth_service() -> ZitadelAuthService:
    """Provide the Zitadel verifier built from platform settings (ADR-0015 (c))."""
    global _zitadel_auth_service
    if _zitadel_auth_service is None:
        _zitadel_auth_service = ZitadelAuthService(
            issuer=settings.zitadel_issuer,
            audience=settings.zitadel_audience,
            jwks_url=settings.zitadel_jwks_url,
        )
    return _zitadel_auth_service


def set_zitadel_auth_service(service: ZitadelAuthService | None) -> None:
    """Override the Zitadel verifier for tests."""
    global _zitadel_auth_service
    _zitadel_auth_service = service


get_principal = require_principal(get_zitadel_auth_service)


def verified_user_id(principal: Annotated[VerifiedPrincipal, Depends(get_principal)]) -> str:
    """Project the verified token subject. Every route in this service requires it."""
    return principal.user_id


VerifiedUserId = Annotated[str, Depends(verified_user_id)]


async def check_user_can_control_soundscape(
    user_id: str,
    session_id: str,
    campaign_id: UUID | None,
    spicedb: SpiceDBClient,
) -> bool:
    """Check Zanzibar authorization for managing audio soundscapes."""
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
    await deliver_best_effort(
        "in-memory", event.event_type, platform_bus.publish(event.event_type, event)
    )
    bus = get_event_bus()
    if bus:
        await publish_best_effort(bus, "runefoble.events.soundscape", event)
