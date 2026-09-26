"""Dependency injection and shared state for Campaign Lore service."""

from typing import Annotated
from uuid import UUID

from fastapi import Header
from runefoble_auth.spicedb import SpiceDBClient
from runefoble_platform.config import PlatformSettings
from runefoble_platform.event_sourcing import (
    AggregateRepository,
    create_aggregate_repository,
)

from campaign_lore.aggregate import LoreDocumentAggregate
from campaign_lore.retrieval import LoreRetrievalEngine

settings = PlatformSettings()

# Global singletons
_repo: AggregateRepository[LoreDocumentAggregate] = create_aggregate_repository(
    LoreDocumentAggregate
)
_retrieval_engine: LoreRetrievalEngine = LoreRetrievalEngine()
_spicedb_client: SpiceDBClient = SpiceDBClient(
    endpoint=settings.spicedb_endpoint or "localhost:50051",
    token=getattr(settings, "spicedb_token", "secret"),
)


def get_repo() -> AggregateRepository[LoreDocumentAggregate]:
    """Provide LoreDocument aggregate repository."""
    return _repo


def get_retrieval_engine() -> LoreRetrievalEngine:
    """Provide redstring hybrid retrieval engine singleton."""
    return _retrieval_engine


def get_spicedb_client() -> SpiceDBClient:
    """Provide SpiceDB Zanzibar authorization client."""
    return _spicedb_client


async def check_user_can_read_secrets(
    user_id: str | None,
    campaign_id: UUID,
    spicedb: SpiceDBClient,
) -> bool:
    """Evaluate SpiceDB Zanzibar permissions to check whether user can read secret DM lore."""
    if not user_id:
        return False
    # Check campaign run_session permission (DM, GM, owner)
    return await spicedb.check_permission(
        resource_type="campaign",
        resource_id=str(campaign_id),
        permission="run_session",
        subject_type="user",
        subject_id=user_id,
    )


async def check_user_can_view_campaign(
    user_id: str | None,
    campaign_id: UUID,
    spicedb: SpiceDBClient,
) -> bool:
    """Evaluate SpiceDB Zanzibar permissions to check whether user can view campaign lore."""
    if not user_id:
        return True  # If no auth is configured/provided, allow public viewing
    return await spicedb.check_permission(
        resource_type="campaign",
        resource_id=str(campaign_id),
        permission="view",
        subject_type="user",
        subject_id=user_id,
    )


def get_current_user_id(
    x_user_id: Annotated[str | None, Header(alias="x-user-id")] = None,
) -> str | None:
    """Extract authenticated caller identity from x-user-id header."""
    return x_user_id
