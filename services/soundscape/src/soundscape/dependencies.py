"""Shared dependency injection, repositories, mixer, and event bus for Soundscape."""

from __future__ import annotations

import logging
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import Depends
from runefoble_auth.principal import VerifiedPrincipal, require_principal
from runefoble_auth.spicedb import SpiceDBClient
from runefoble_auth.zitadel import ZitadelAuthService
from runefoble_events.base import BaseRunefobleEvent
from runefoble_platform.bus import bus as platform_bus
from runefoble_platform.config import PlatformSettings
from runefoble_platform.event_bus import EventBusProvider
from runefoble_platform.event_publish import deliver_best_effort, publish_best_effort
from runefoble_platform.event_sourcing import AggregateRepository, create_aggregate_repository

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

_soundscape_repo = create_aggregate_repository(SoundscapeAggregate)

_session_to_aggregate: dict[str, UUID] = {}
_session_mixers: dict[str, AudioStemMixer] = {}
_session_leitmotif_engines: dict[str, LeitmotifEngine] = {}
_zitadel_auth_service: ZitadelAuthService | None = None


def get_soundscape_repo() -> AggregateRepository[SoundscapeAggregate]:
    """Provide SoundscapeAggregate repository singleton."""
    return _soundscape_repo


event_bus_provider = EventBusProvider(settings)
get_event_bus = event_bus_provider.get
set_event_bus = event_bus_provider.set


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
    _session_to_aggregate.clear()
    _session_mixers.clear()
    _session_leitmotif_engines.clear()
    event_bus_provider.set(None)


def get_zitadel_auth_service() -> ZitadelAuthService:
    """Provide the Zitadel verifier built from platform settings (ADR-0015 (c))."""
    global _zitadel_auth_service
    if _zitadel_auth_service is None:
        _zitadel_auth_service = ZitadelAuthService(
            issuer=settings.zitadel_issuer,
            audience=settings.zitadel_audience,
            internal_url=settings.zitadel_internal_url,
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
    """Check the schema permissions that govern soundscape controls (ADR-0001).

    The subject needs `session.control` on the session, or `campaign.run_session` on the
    campaign when the request names one. A SpiceDB failure raises and is never a denial.
    """
    if await spicedb.check_permission("session", session_id, "control", "user", user_id):
        return True
    if campaign_id is None:
        return False
    return await spicedb.check_permission(
        "campaign", str(campaign_id), "run_session", "user", user_id
    )


async def check_user_can_trigger_cue(
    user_id: str,
    session_id: str,
    campaign_id: UUID | None,
    spicedb: SpiceDBClient,
) -> bool:
    """Check whether the subject may trigger a foley cue.

    Players who take part in the session may trigger cues (`session.participate`). Controllers
    and campaign run-session roles may too. A SpiceDB failure raises and is never a denial.
    """
    if await check_user_can_control_soundscape(user_id, session_id, campaign_id, spicedb):
        return True
    if await spicedb.check_permission("session", session_id, "participate", "user", user_id):
        return True
    if campaign_id is None:
        return False
    return await spicedb.check_permission("campaign", str(campaign_id), "play", "user", user_id)


async def publish_soundscape_event(event: BaseRunefobleEvent) -> None:
    """Publish soundscape domain event across in-memory platform bus and Redis Streams."""
    await deliver_best_effort(
        "in-memory", event.event_type, platform_bus.publish(event.event_type, event)
    )
    bus = get_event_bus()
    if bus:
        await publish_best_effort(bus, "runefoble.events.soundscape", event)
