"""Dependency injection and shared state for Campaign Lore service."""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
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


async def require_campaign_view(
    user_id: str | None,
    campaign_id: UUID,
    spicedb: SpiceDBClient,
) -> None:
    """Raise HTTP 403 if user cannot view the campaign."""
    can_view = await check_user_can_view_campaign(user_id, campaign_id, spicedb)
    if not can_view:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Cannot access campaign codex.",
        )


async def load_codex_entry(
    campaign_id: UUID,
    entry_id: UUID,
    user_id: str | None,
    repo: AggregateRepository[CodexAggregate],
    spicedb: SpiceDBClient,
    *,
    for_edit: bool = False,
) -> CodexAggregate:
    """Load a codex entry aggregate and enforce SpiceDB Zanzibar view or edit permissions."""
    try:
        aggregate = await repo.load(entry_id)
        state = aggregate.state
    except Exception as exc:
        raise HTTPException(status_code=404, detail="Codex entry not found") from exc

    if for_edit:
        can_edit = await check_user_can_edit_codex_entry(user_id, state, campaign_id, spicedb)
        if not can_edit:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: Not authorized to edit this codex entry.",
            )
    else:
        can_read = await check_user_can_view_codex_entry(user_id, state, campaign_id, spicedb)
        if not can_read:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: SpiceDB Zanzibar policy denies access to this private codex entry.",
            )

    return aggregate


async def write_codex_permissions(
    spicedb: SpiceDBClient,
    entry_id: str,
    author_id: str,
    campaign_id: str,
    privacy: str,
) -> None:
    """Write initial SpiceDB Zanzibar ownership and privacy relations for a new codex entry."""
    await spicedb.write_relationship(
        resource_type="codex_entry",
        resource_id=entry_id,
        relation="author",
        subject_type="user",
        subject_id=author_id,
    )
    await spicedb.write_relationship(
        resource_type="codex_entry",
        resource_id=entry_id,
        relation="editor",
        subject_type="user",
        subject_id=author_id,
    )
    await spicedb.write_relationship(
        resource_type="codex_entry",
        resource_id=entry_id,
        relation="campaign",
        subject_type="campaign",
        subject_id=campaign_id,
    )
    if privacy == "party_shared":
        await spicedb.write_relationship(
            resource_type="codex_entry",
            resource_id=entry_id,
            relation="party_shared",
            subject_type="campaign",
            subject_id=campaign_id,
        )
    elif privacy == "public":
        await spicedb.write_relationship(
            resource_type="codex_entry",
            resource_id=entry_id,
            relation="public",
            subject_type="campaign",
            subject_id=campaign_id,
        )


async def update_codex_permissions(
    spicedb: SpiceDBClient,
    entry_id: str,
    campaign_id: str,
    old_privacy: str,
    new_privacy: str,
) -> None:
    """Synchronize SpiceDB Zanzibar privacy relations when a codex entry privacy changes."""
    if old_privacy == "party_shared":
        await spicedb.delete_relationship(
            "codex_entry", entry_id, "party_shared", "campaign", campaign_id
        )
    elif old_privacy == "public":
        await spicedb.delete_relationship(
            "codex_entry", entry_id, "public", "campaign", campaign_id
        )

    if new_privacy == "party_shared":
        await spicedb.write_relationship(
            "codex_entry", entry_id, "party_shared", "campaign", campaign_id
        )
    elif new_privacy == "public":
        await spicedb.write_relationship("codex_entry", entry_id, "public", "campaign", campaign_id)


class CodexSessionDeps:
    """Consolidated dependencies for codex session, aggregate repo, and SpiceDB client."""

    def __init__(
        self,
        user_id: Annotated[str | None, Depends(get_current_user_id)],
        repo: Annotated[AggregateRepository[CodexAggregate], Depends(get_codex_repo)],
        spicedb: Annotated[SpiceDBClient, Depends(get_spicedb_client)],
    ) -> None:
        self.user_id = user_id
        self.repo = repo
        self.spicedb = spicedb

    async def can_view(self, st: CodexEntryState, campaign_id: UUID) -> bool:
        """Check whether authenticated user can view codex entry under Zanzibar."""
        return await check_user_can_view_codex_entry(self.user_id, st, campaign_id, self.spicedb)

    async def persist_new_entry(
        self,
        agg: CodexAggregate,
        campaign_id: UUID,
        author_id: str,
        privacy: str,
        idx: dict[UUID, list[UUID]],
    ) -> None:
        """Persist aggregate to event store and write SpiceDB authorization tuples."""
        await self.repo.save(agg)
        idx.setdefault(campaign_id, []).append(agg.aggregate_id)
        await write_codex_permissions(
            self.spicedb, str(agg.aggregate_id), author_id, str(campaign_id), privacy
        )

    async def persist_updated_entry(
        self,
        agg: CodexAggregate,
        campaign_id: UUID,
        entry_id: UUID,
        old_privacy: str,
        new_privacy: str | None,
    ) -> None:
        """Persist updated aggregate and sync revised SpiceDB authorization tuples."""
        await self.repo.save(agg)
        if new_privacy and new_privacy != old_privacy:
            await update_codex_permissions(
                self.spicedb, str(entry_id), str(campaign_id), old_privacy, new_privacy
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
