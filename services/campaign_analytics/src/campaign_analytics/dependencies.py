"""Dependency injection container and authorization helpers for Campaign Analytics microservice."""

from __future__ import annotations

import contextlib
from typing import Annotated

from fastapi import Depends
from runefoble_auth.spicedb import MockSpiceDBClient, SpiceDBClient
from runefoble_platform.config import PlatformSettings
from runefoble_platform.redis_bus import RedisStreamsEventBus

from campaign_analytics.storage import CampaignAnalyticsStorage
from campaign_analytics.worker import CampaignAnalyticsWorker

platform_settings = PlatformSettings()

_storage: CampaignAnalyticsStorage = CampaignAnalyticsStorage()
_worker: CampaignAnalyticsWorker | None = None
_spicedb_client: SpiceDBClient | MockSpiceDBClient | None = None
_event_bus: RedisStreamsEventBus | None = None


def get_storage() -> CampaignAnalyticsStorage:
    """Provide initialized CampaignAnalyticsStorage."""
    return _storage


def set_storage(storage: CampaignAnalyticsStorage) -> None:
    """Override CampaignAnalyticsStorage instance (e.g. for testing)."""
    global _storage
    _storage = storage


def get_worker() -> CampaignAnalyticsWorker | None:
    """Provide CampaignAnalyticsWorker instance."""
    return _worker


def set_worker(worker: CampaignAnalyticsWorker | None) -> None:
    """Override CampaignAnalyticsWorker instance."""
    global _worker
    _worker = worker


def get_spicedb_client() -> SpiceDBClient | MockSpiceDBClient:
    """Provide SpiceDB Zanzibar authorization client."""
    global _spicedb_client
    if _spicedb_client is None:
        _spicedb_client = SpiceDBClient()
    return _spicedb_client


def set_spicedb_client(client: SpiceDBClient | MockSpiceDBClient | None) -> None:
    """Override SpiceDB Zanzibar client."""
    global _spicedb_client
    _spicedb_client = client


def get_event_bus() -> RedisStreamsEventBus | None:
    """Provide RedisStreamsEventBus instance."""
    global _event_bus
    if _event_bus is None and platform_settings.redis_url:
        with contextlib.suppress(Exception):
            _event_bus = RedisStreamsEventBus(redis_url=platform_settings.redis_url)
    return _event_bus


def set_event_bus(bus: RedisStreamsEventBus | None) -> None:
    """Override event bus instance."""
    global _event_bus
    _event_bus = bus


async def check_user_can_view_campaign(
    user_id: str | None,
    campaign_id: str,
    spicedb: SpiceDBClient | MockSpiceDBClient,
) -> bool:
    """Evaluate SpiceDB Zanzibar permissions to check whether user can view campaign analytics."""
    if not user_id:
        return True  # Public viewing permitted when no user specified
    return await spicedb.check_permission(
        resource_type="campaign",
        resource_id=str(campaign_id),
        permission="view",
        subject_type="user",
        subject_id=user_id,
    )


StorageDep = Annotated[CampaignAnalyticsStorage, Depends(get_storage)]
SpiceDep = Annotated[SpiceDBClient | MockSpiceDBClient, Depends(get_spicedb_client)]
