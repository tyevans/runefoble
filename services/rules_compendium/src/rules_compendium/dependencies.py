"""Dependency injection and shared singletons for the Rules Compendium service."""

from typing import Annotated
from uuid import UUID

from fastapi import Header
from runefoble_auth.spicedb import SpiceDBClient
from runefoble_platform.config import PlatformSettings
from runefoble_platform.event_sourcing import (
    AggregateRepository,
    create_aggregate_repository,
)

from rules_compendium.aggregate import CompendiumAggregate, EncounterAggregate
from rules_compendium.retrieval import CompendiumRetrievalEngine

settings = PlatformSettings()

# Global singletons
_compendium_repo: AggregateRepository[CompendiumAggregate] = create_aggregate_repository(
    CompendiumAggregate
)
_encounter_repo: AggregateRepository[EncounterAggregate] = create_aggregate_repository(
    EncounterAggregate
)
_retrieval_engine: CompendiumRetrievalEngine = CompendiumRetrievalEngine()
_spicedb_client: SpiceDBClient = SpiceDBClient(
    endpoint=settings.spicedb_endpoint or "localhost:50051",
    token=getattr(settings, "spicedb_token", "secret"),
)


def get_compendium_repo() -> AggregateRepository[CompendiumAggregate]:
    """Provide CompendiumAggregate repository."""
    return _compendium_repo


def get_encounter_repo() -> AggregateRepository[EncounterAggregate]:
    """Provide EncounterAggregate repository."""
    return _encounter_repo


def get_retrieval_engine() -> CompendiumRetrievalEngine:
    """Provide CompendiumRetrievalEngine singleton."""
    return _retrieval_engine


def get_spicedb_client() -> SpiceDBClient:
    """Provide SpiceDB Zanzibar client."""
    return _spicedb_client


def get_current_user_id(
    x_user_id: Annotated[str | None, Header(alias="x-user-id")] = None,
) -> str | None:
    """Extract authenticated caller identity from x-user-id header."""
    return x_user_id


async def check_user_can_view_campaign(
    user_id: str | None,
    campaign_id: UUID,
    spicedb: SpiceDBClient,
) -> bool:
    """Check if user can view campaign resources under Zanzibar schema."""
    if not user_id:
        return True
    return await spicedb.check_permission(
        resource_type="campaign",
        resource_id=str(campaign_id),
        permission="view",
        subject_type="user",
        subject_id=user_id,
    )


async def check_user_can_manage_homebrew(
    user_id: str | None,
    campaign_id: UUID,
    spicedb: SpiceDBClient,
) -> bool:
    """Check if user can manage/register homebrew rules under Zanzibar schema."""
    if not user_id:
        return False
    # Check if user has manage or run_session on campaign
    can_run = await spicedb.check_permission(
        resource_type="campaign",
        resource_id=str(campaign_id),
        permission="run_session",
        subject_type="user",
        subject_id=user_id,
    )
    if can_run:
        return True
    return await spicedb.check_permission(
        resource_type="campaign",
        resource_id=str(campaign_id),
        permission="manage",
        subject_type="user",
        subject_id=user_id,
    )
