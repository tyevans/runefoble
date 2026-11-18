"""Dependency injection container and authorization helpers for Campaign Analytics microservice."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from runefoble_auth.factory import get_spicedb_client
from runefoble_auth.principal import VerifiedPrincipal, require_principal
from runefoble_auth.spicedb import SpiceDBClient
from runefoble_auth.zitadel import ZitadelAuthService
from runefoble_platform.config import PlatformSettings

from campaign_analytics.storage import CampaignAnalyticsStorage, StorageUnavailableError
from campaign_analytics.worker import CampaignAnalyticsWorker

platform_settings = PlatformSettings()

_storage: CampaignAnalyticsStorage | None = None
_worker: CampaignAnalyticsWorker | None = None
_zitadel_auth_service: ZitadelAuthService | None = None


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


def get_zitadel_auth_service() -> ZitadelAuthService:
    """Provide the Zitadel verifier that this service trusts, built from platform settings."""
    global _zitadel_auth_service
    if _zitadel_auth_service is None:
        _zitadel_auth_service = ZitadelAuthService(
            issuer=platform_settings.zitadel_issuer,
            audience=platform_settings.zitadel_audience,
            internal_url=platform_settings.zitadel_internal_url,
        )
    return _zitadel_auth_service


def set_zitadel_auth_service(service: ZitadelAuthService | None) -> None:
    """Override the Zitadel verifier for tests."""
    global _zitadel_auth_service
    _zitadel_auth_service = service


get_current_principal = require_principal(get_zitadel_auth_service)


def get_current_user_id(
    principal: Annotated[VerifiedPrincipal, Depends(get_current_principal)],
) -> str:
    """Return the subject of the verified bearer token. Raise 401 when no token verifies."""
    return principal.user_id


async def check_user_can_view_campaign(
    user_id: str,
    campaign_id: str,
    spicedb: SpiceDBClient,
) -> bool:
    """Evaluate SpiceDB Zanzibar permissions to check whether user can view campaign analytics.

    A SpiceDB failure raises AuthzUnavailableError. It never returns False.
    """
    return await spicedb.check_permission(
        resource_type="campaign",
        resource_id=str(campaign_id),
        permission="view",
        subject_type="user",
        subject_id=user_id,
    )


CurrentUserId = Annotated[str, Depends(get_current_user_id)]
StorageDep = Annotated[CampaignAnalyticsStorage, Depends(get_storage)]
SpiceDep = Annotated[SpiceDBClient, Depends(get_spicedb_client)]
