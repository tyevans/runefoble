"""Shared dependency injection, repositories, storage, and event bus for Asset Forge."""

from __future__ import annotations

import logging
from typing import Annotated
from uuid import UUID

from fastapi import Depends
from runefoble_auth.principal import VerifiedPrincipal, require_principal
from runefoble_auth.spicedb import MockSpiceDBClient, SpiceDBClient
from runefoble_auth.zitadel import ZitadelAuthService
from runefoble_events.base import BaseRunefobleEvent
from runefoble_platform.bus import bus as platform_bus
from runefoble_platform.config import PlatformSettings, WardrobeGeneratorSettings
from runefoble_platform.event_bus import EventBusProvider
from runefoble_platform.event_publish import deliver_best_effort, publish_best_effort
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
_spicedb_client: SpiceDBClient | MockSpiceDBClient | None = None
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


async def check_user_can_forge(
    user_id: str,
    campaign_id: UUID | None,
    spicedb: SpiceDBClient | MockSpiceDBClient,
) -> bool:
    """Check Zanzibar authorization for forging assets in campaign context."""
    if not campaign_id:
        # Standalone forge without campaign context is permissible
        return True

    # Check play or run_session or manage on campaign
    can_play = await spicedb.check_permission(
        resource_type="campaign",
        resource_id=str(campaign_id),
        permission="play",
        subject_type="user",
        subject_id=user_id,
    )
    if can_play:
        return True

    return await spicedb.check_permission(
        resource_type="campaign",
        resource_id=str(campaign_id),
        permission="run_session",
        subject_type="user",
        subject_id=user_id,
    )


async def publish_forge_event(event: BaseRunefobleEvent) -> None:
    """Publish forge domain event across in-memory platform bus and Redis Streams."""
    # 1. In-memory bus
    await deliver_best_effort(
        "in-memory", event.event_type, platform_bus.publish(event.event_type, event)
    )

    # 2. Redis stream bus
    bus = get_event_bus()
    if bus:
        stream = "runefoble.events.asset"
        await publish_best_effort(bus, stream, event)
