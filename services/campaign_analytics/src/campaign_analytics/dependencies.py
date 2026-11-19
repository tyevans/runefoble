"""Dependency injection container and authorization helpers for Campaign Analytics microservice."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from runefoble_auth.factory import get_spicedb_client
from runefoble_auth.permissions import check_subject
from runefoble_auth.spicedb import SpiceDBClient
from runefoble_auth.wiring import (
    build_identity_dependencies,
    make_verifier_holder,
    verifier_from_settings,
)
from runefoble_platform.config import PlatformSettings

from campaign_analytics.storage import CampaignAnalyticsStorage, StorageUnavailableError
from campaign_analytics.worker import CampaignAnalyticsWorker

platform_settings = PlatformSettings()

_storage: CampaignAnalyticsStorage | None = None
_worker: CampaignAnalyticsWorker | None = None


def get_storage() -> CampaignAnalyticsStorage:
    """Provide the PostgreSQL-backed storage. Raise while the service has not started it."""
    if _storage is None:
        raise StorageUnavailableError("Campaign analytics storage has not been started")
    return _storage


def set_storage(storage: CampaignAnalyticsStorage | None) -> None:
    """Set or clear the storage that the process-wide container serves."""
    global _storage
    _storage = storage


def get_worker() -> CampaignAnalyticsWorker | None:
    """Provide CampaignAnalyticsWorker instance."""
    return _worker


def set_worker(worker: CampaignAnalyticsWorker | None) -> None:
    """Override CampaignAnalyticsWorker instance."""
    global _worker
    _worker = worker


get_zitadel_auth_service, set_zitadel_auth_service = make_verifier_holder(
    lambda: verifier_from_settings(platform_settings)
)
get_principal, CallerPrincipal, CallerId, get_caller_or_service, CallerOrService = (
    build_identity_dependencies(get_zitadel_auth_service, None)
)


async def check_user_can_view_campaign(
    user_id: str,
    campaign_id: str,
    spicedb: SpiceDBClient,
) -> bool:
    """Evaluate SpiceDB Zanzibar permissions to check whether user can view campaign analytics.

    A SpiceDB failure raises AuthzUnavailableError. It never returns False.
    """
    return await check_subject(spicedb, "campaign", str(campaign_id), "view", user_id)


StorageDep = Annotated[CampaignAnalyticsStorage, Depends(get_storage)]
SpiceDep = Annotated[SpiceDBClient, Depends(get_spicedb_client)]
