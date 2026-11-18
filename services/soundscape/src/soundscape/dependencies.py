"""Shared dependency injection, event repository, and bus seams for Soundscape.

Process-local state is limited to seams (the Zitadel verifier and the event bus). Session
state lives only in the event-sourced soundscape aggregate.
"""

from __future__ import annotations

import logging
from typing import Annotated
from uuid import UUID

from fastapi import Depends
from runefoble_auth.principal import VerifiedPrincipal, require_principal
from runefoble_auth.spicedb import SpiceDBClient
from runefoble_auth.zitadel import ZitadelAuthService
from runefoble_events.base import BaseRunefobleEvent
from runefoble_platform.config import PlatformSettings
from runefoble_platform.event_bus import EventBusProvider
from runefoble_platform.event_publish import publish_best_effort
from runefoble_platform.event_sourcing import AggregateRepository, create_aggregate_repository

from soundscape.aggregate import SoundscapeAggregate

logger = logging.getLogger("runefoble.soundscape")
settings = PlatformSettings()

_zitadel_auth_service: ZitadelAuthService | None = None


def get_soundscape_repo() -> AggregateRepository[SoundscapeAggregate]:
    """Return a repository on the process event store. No aggregate is cached in memory."""
    return create_aggregate_repository(SoundscapeAggregate)


event_bus_provider = EventBusProvider(settings)
get_event_bus = event_bus_provider.get
set_event_bus = event_bus_provider.set


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
    """Publish a soundscape domain event on the soundscape Redis stream.

    Policy: best effort. The aggregate is already saved, so a failed publish is logged and
    counted on `/healthz`. It does not fail the request.
    """
    await publish_best_effort(get_event_bus(), "runefoble.events.soundscape", event)
