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
from campaign_lore.atlas_aggregate import AtlasAggregate
from campaign_lore.codex import CodexCrossReferencer
from campaign_lore.codex_aggregate import CodexAggregate, CodexEntryState
from campaign_lore.handouts_aggregate import (
    DiegeticHandoutAggregate,
    RelicAggregate,
)
from campaign_lore.retrieval import LoreRetrievalEngine
from campaign_lore.west_marches_aggregate import WestMarchesAtlasAggregate

settings = PlatformSettings()

# Global singletons
_repo: AggregateRepository[LoreDocumentAggregate] = create_aggregate_repository(
    LoreDocumentAggregate
)
_handout_repo: AggregateRepository[DiegeticHandoutAggregate] = create_aggregate_repository(
    DiegeticHandoutAggregate
)
_relic_repo: AggregateRepository[RelicAggregate] = create_aggregate_repository(RelicAggregate)
_atlas_repo: AggregateRepository[AtlasAggregate] = create_aggregate_repository(AtlasAggregate)
_codex_repo: AggregateRepository[CodexAggregate] = create_aggregate_repository(CodexAggregate)
_west_marches_repo: AggregateRepository[WestMarchesAtlasAggregate] = create_aggregate_repository(
    WestMarchesAtlasAggregate
)
_retrieval_engine: LoreRetrievalEngine = LoreRetrievalEngine()
_codex_referencer: CodexCrossReferencer = CodexCrossReferencer(_retrieval_engine)
_campaign_codex_entries: dict[UUID, list[UUID]] = {}
_spicedb_client: SpiceDBClient = SpiceDBClient(
    endpoint=settings.spicedb_endpoint or "localhost:50051",
    token=getattr(settings, "spicedb_token", "secret"),
)


def get_repo() -> AggregateRepository[LoreDocumentAggregate]:
    """Provide LoreDocument aggregate repository."""
    return _repo


def get_handout_repo() -> AggregateRepository[DiegeticHandoutAggregate]:
    """Provide DiegeticHandout aggregate repository."""
    return _handout_repo


def get_relic_repo() -> AggregateRepository[RelicAggregate]:
    """Provide Relic aggregate repository."""
    return _relic_repo


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


async def check_user_can_interact_handout(
    user_id: str | None,
    campaign_id: UUID,
    spicedb: SpiceDBClient,
) -> bool:
    """Evaluate SpiceDB Zanzibar permissions to check whether user can break seal or interact with handout."""
    if not user_id:
        return True
    return await spicedb.check_permission(
        resource_type="campaign",
        resource_id=str(campaign_id),
        permission="play",
        subject_type="user",
        subject_id=user_id,
    )


async def check_user_can_inspect_relic(
    user_id: str | None,
    campaign_id: UUID,
    spicedb: SpiceDBClient,
) -> bool:
    """Evaluate SpiceDB Zanzibar permissions to check whether user can view and inspect relic."""
    if not user_id:
        return True
    return await spicedb.check_permission(
        resource_type="campaign",
        resource_id=str(campaign_id),
        permission="view",
        subject_type="user",
        subject_id=user_id,
    )


def get_atlas_repo() -> AggregateRepository[AtlasAggregate]:
    """Provide Atlas aggregate repository."""
    return _atlas_repo


def get_codex_repo() -> AggregateRepository[CodexAggregate]:
    """Provide Codex aggregate repository."""
    return _codex_repo


def get_codex_referencer() -> CodexCrossReferencer:
    """Provide Codex cross-referencer engine."""
    return _codex_referencer


def get_campaign_codex_index() -> dict[UUID, list[UUID]]:
    """Provide in-memory campaign codex entry index."""
    return _campaign_codex_entries


async def check_user_can_view_codex_entry(
    user_id: str | None,
    entry: CodexEntryState,
    campaign_id: UUID,
    spicedb: SpiceDBClient,
) -> bool:
    """Evaluate SpiceDB Zanzibar permissions to check whether user can read a codex entry."""
    if not user_id:
        return entry.privacy == "public"

    # Author always has view access
    if entry.author_id and entry.author_id == user_id:
        return True

    # Check direct Zanzibar permission on codex_entry
    allowed = await spicedb.check_permission(
        resource_type="codex_entry",
        resource_id=str(entry.entry_id),
        permission="view",
        subject_type="user",
        subject_id=user_id,
    )
    if allowed:
        return True

    # If party_shared, campaign players and DMs can view
    if entry.privacy == "party_shared":
        can_play = await spicedb.check_permission(
            resource_type="campaign",
            resource_id=str(campaign_id),
            permission="play",
            subject_type="user",
            subject_id=user_id,
        )
        if can_play:
            return True
        can_run = await spicedb.check_permission(
            resource_type="campaign",
            resource_id=str(campaign_id),
            permission="run_session",
            subject_type="user",
            subject_id=user_id,
        )
        if can_run:
            return True

    # If public, any campaign viewer can view
    if entry.privacy == "public":
        return await spicedb.check_permission(
            resource_type="campaign",
            resource_id=str(campaign_id),
            permission="view",
            subject_type="user",
            subject_id=user_id,
        )

    return False


async def check_user_can_edit_codex_entry(
    user_id: str | None,
    entry: CodexEntryState,
    campaign_id: UUID,
    spicedb: SpiceDBClient,
) -> bool:
    """Evaluate SpiceDB Zanzibar permissions to check whether user can edit a codex entry."""
    if not user_id:
        return False

    if entry.author_id and entry.author_id == user_id:
        return True

    # Check direct edit permission on codex_entry
    allowed = await spicedb.check_permission(
        resource_type="codex_entry",
        resource_id=str(entry.entry_id),
        permission="edit",
        subject_type="user",
        subject_id=user_id,
    )
    if allowed:
        return True

    # DM / GM can edit entries
    return await spicedb.check_permission(
        resource_type="campaign",
        resource_id=str(campaign_id),
        permission="run_session",
        subject_type="user",
        subject_id=user_id,
    )


def get_west_marches_repo() -> AggregateRepository[WestMarchesAtlasAggregate]:
    """Provide West Marches shared atlas and stronghold aggregate repository."""
    return _west_marches_repo


def set_west_marches_repo(
    repo: AggregateRepository[WestMarchesAtlasAggregate],
) -> None:
    """Set West Marches repository instance for testing."""
    global _west_marches_repo
    _west_marches_repo = repo


def set_spicedb_client(client: SpiceDBClient) -> None:
    """Override SpiceDB client instance for testing."""
    global _spicedb_client
    _spicedb_client = client


async def check_user_can_play_campaign(
    user_id: str | None,
    campaign_id: UUID,
    spicedb: SpiceDBClient,
) -> bool:
    """Evaluate SpiceDB Zanzibar permissions to check whether user can play or discover in campaign."""
    if not user_id:
        return True
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
