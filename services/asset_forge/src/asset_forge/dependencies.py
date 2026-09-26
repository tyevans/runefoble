"""Shared dependency injection, repositories, storage, and event bus for Asset Forge."""

from __future__ import annotations

import contextlib
import logging
from typing import Annotated
from uuid import UUID

from fastapi import Header
from runefoble_auth.spicedb import SpiceDBClient
from runefoble_events.base import BaseRunefobleEvent
from runefoble_platform.bus import bus as platform_bus
from runefoble_platform.config import PlatformSettings
from runefoble_platform.event_sourcing import (
    AggregateRepository,
    create_aggregate_repository,
)
from runefoble_platform.redis_bus import RedisStreamsEventBus
from runefoble_platform.storage import SiloStorageService
from runefoble_platform.storage import get_storage_service as get_platform_storage

from asset_forge.aggregate import AssetForgeAggregate

logger = logging.getLogger("runefoble.asset_forge")
settings = PlatformSettings()

_event_bus: RedisStreamsEventBus | None = None
_storage_service: SiloStorageService | None = None
_forge_repo: AggregateRepository[AssetForgeAggregate] = create_aggregate_repository(
    AssetForgeAggregate
)
_spicedb_client: SpiceDBClient = SpiceDBClient(
    endpoint=settings.spicedb_endpoint or "localhost:50051",
    token=getattr(settings, "spicedb_token", "secret"),
)


def get_forge_repo() -> AggregateRepository[AssetForgeAggregate]:
    """Provide AssetForgeAggregate repository singleton."""
    return _forge_repo


def get_storage() -> SiloStorageService:
    """Provide Silo storage service instance."""
    global _storage_service
    if _storage_service is None:
        _storage_service = get_platform_storage()
    return _storage_service


def set_storage(storage: SiloStorageService | None) -> None:
    """Override storage service for testing."""
    global _storage_service
    _storage_service = storage


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


def get_spicedb_client() -> SpiceDBClient:
    """Provide SpiceDB Zanzibar authorization client."""
    return _spicedb_client


def get_current_user_id(
    x_user_id: Annotated[str | None, Header(alias="x-user-id")] = None,
) -> str | None:
    """Extract authenticated caller identity from x-user-id header."""
    return x_user_id


async def check_user_can_forge(
    user_id: str | None,
    campaign_id: UUID | None,
    spicedb: SpiceDBClient,
) -> bool:
    """Check Zanzibar authorization for forging assets in campaign context."""
    if not campaign_id or not user_id:
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
    with contextlib.suppress(Exception):
        await platform_bus.publish(event.event_type, event)

    # 2. Redis stream bus
    bus = get_event_bus()
    if bus:
        stream = "runefoble.events.asset"
        with contextlib.suppress(Exception):
            await bus.publish_event(stream, event)
