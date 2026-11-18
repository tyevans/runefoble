"""Shared dependency injection, repositories, storage, and event bus for Asset Forge."""

from __future__ import annotations

import logging
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException
from runefoble_auth.principal import VerifiedPrincipal, require_principal
from runefoble_auth.spicedb import SpiceDBClient
from runefoble_auth.zitadel import ZitadelAuthService
from runefoble_events.base import BaseRunefobleEvent
from runefoble_platform.config import PlatformSettings, WardrobeGeneratorSettings
from runefoble_platform.event_bus import EventBusProvider
from runefoble_platform.event_publish import publish_best_effort
from runefoble_platform.event_sourcing import (
    AggregateRepository,
    create_aggregate_repository,
)
from runefoble_platform.storage import SiloStorageService
from runefoble_platform.storage import get_storage_service as get_platform_storage

from asset_forge.aggregate import AssetForgeAggregate
from asset_forge.wardrobe_generator import WardrobeGenerator, build_wardrobe_generator

logger = logging.getLogger("runefoble.asset_forge")
settings = PlatformSettings()

_forge_repo: AggregateRepository[AssetForgeAggregate] = create_aggregate_repository(
    AssetForgeAggregate
)
_wardrobe_generator: WardrobeGenerator | None = None
_zitadel_auth_service: ZitadelAuthService | None = None


def get_forge_repo() -> AggregateRepository[AssetForgeAggregate]:
    """Provide AssetForgeAggregate repository singleton."""
    return _forge_repo


def get_storage() -> SiloStorageService:
    """Provide the platform Silo storage client."""
    return get_platform_storage()


def get_wardrobe_generator() -> WardrobeGenerator:
    """Provide the configured wardrobe generator (placeholder by default)."""
    global _wardrobe_generator
    if _wardrobe_generator is None:
        _wardrobe_generator = build_wardrobe_generator(WardrobeGeneratorSettings())
    return _wardrobe_generator


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


async def require_forge_permission(
    user_id: str,
    campaign_id: UUID | None,
    spicedb: SpiceDBClient,
) -> UUID:
    """Allow a forge action only for a campaign player (`campaign.play`).

    Returns the campaign id, so the caller holds a non-optional value.

    Raises:
        HTTPException: 400 when no campaign is named, 403 when the caller lacks `play`.
    """
    if campaign_id is None:
        raise HTTPException(status_code=400, detail="A campaign_id is required to forge assets.")
    allowed = await spicedb.check_permission(
        resource_type="campaign",
        resource_id=str(campaign_id),
        permission="play",
        subject_type="user",
        subject_id=user_id,
    )
    if not allowed:
        raise HTTPException(
            status_code=403,
            detail=f"Forbidden: User '{user_id}' cannot forge assets for campaign '{campaign_id}'.",
        )
    return campaign_id


async def record_asset_relations(
    spicedb: SpiceDBClient,
    asset_id: str,
    creator_id: str,
    campaign_id: UUID,
) -> None:
    """Write the `creator` and `campaign` relations of one forged asset.

    No error is suppressed. A failed write raises `AuthzError`, and the route stores nothing.
    """
    await spicedb.write_relationship(
        resource_type="forged_asset",
        resource_id=asset_id,
        relation="creator",
        subject_type="user",
        subject_id=creator_id,
    )
    await spicedb.write_relationship(
        resource_type="forged_asset",
        resource_id=asset_id,
        relation="campaign",
        subject_type="campaign",
        subject_id=str(campaign_id),
    )


async def require_asset_view(spicedb: SpiceDBClient, asset_id: str, user_id: str) -> None:
    """Allow a read only when the caller holds `forged_asset.view` on the asset.

    Raises:
        HTTPException: 403 when the caller lacks the permission.
    """
    allowed = await spicedb.check_permission(
        resource_type="forged_asset",
        resource_id=asset_id,
        permission="view",
        subject_type="user",
        subject_id=user_id,
    )
    if not allowed:
        raise HTTPException(
            status_code=403,
            detail=f"Forbidden: User '{user_id}' cannot view forged asset '{asset_id}'.",
        )


STREAM_ASSET = "runefoble.events.asset"
STREAM_CHARACTER = "runefoble.events.character"


async def publish_forge_event(event: BaseRunefobleEvent, stream: str = STREAM_ASSET) -> None:
    """Publish a forge domain event on the Redis Streams bus.

    Policy: best effort. The route has already stored the asset or the map, so a failed
    publish is logged and counted on `/healthz`. It does not fail the request.
    """
    await publish_best_effort(get_event_bus(), stream, event)
