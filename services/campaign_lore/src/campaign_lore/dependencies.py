"""Dependency injection and shared state for Campaign Lore service."""

from uuid import UUID

from runefoble_auth.spicedb import MockSpiceDBClient, SpiceDBClient
from runefoble_platform.config import PlatformSettings
from runefoble_platform.event_sourcing import AggregateRepository, create_aggregate_repository

from campaign_lore.aggregate import LoreDocumentAggregate
from campaign_lore.atlas_aggregate import AtlasAggregate
from campaign_lore.codex import CodexCrossReferencer
from campaign_lore.codex_aggregate import CodexAggregate
from campaign_lore.codex_deps import (  # noqa: F401
    CodexSessionDeps,
    check_user_can_edit_codex_entry,
    check_user_can_view_codex_entry,
    load_codex_entry,
    require_campaign_view,
    update_codex_permissions,
    write_codex_permissions,
)
from campaign_lore.handouts_aggregate import DiegeticHandoutAggregate, RelicAggregate
from campaign_lore.permissions import (  # noqa: F401
    check_user_can_inspect_relic,
    check_user_can_interact_handout,
    check_user_can_play_campaign,
    check_user_can_read_secrets,
    check_user_can_view_campaign,
    get_current_user_id,
)
from campaign_lore.retrieval import LoreRetrievalEngine
from campaign_lore.west_marches_aggregate import WestMarchesAtlasAggregate

settings = PlatformSettings()

# Global singletons
_repo = create_aggregate_repository(LoreDocumentAggregate)
_handout_repo = create_aggregate_repository(DiegeticHandoutAggregate)
_relic_repo = create_aggregate_repository(RelicAggregate)
_atlas_repo = create_aggregate_repository(AtlasAggregate)
_codex_repo = create_aggregate_repository(CodexAggregate)
_west_marches_repo = create_aggregate_repository(WestMarchesAtlasAggregate)
_retrieval_engine = LoreRetrievalEngine()
_codex_referencer = CodexCrossReferencer(_retrieval_engine)
_campaign_codex_entries: dict[UUID, list[UUID]] = {}
_spicedb_client: SpiceDBClient | MockSpiceDBClient | None = None


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


def get_spicedb_client() -> SpiceDBClient | MockSpiceDBClient:
    """Provide SpiceDB Zanzibar authorization client."""
    global _spicedb_client
    if _spicedb_client is None:
        _spicedb_client = SpiceDBClient(
            endpoint=settings.spicedb_endpoint or "localhost:50051",
            token=getattr(settings, "spicedb_token", "secret"),
        )
    return _spicedb_client


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


def get_west_marches_repo() -> AggregateRepository[WestMarchesAtlasAggregate]:
    """Provide West Marches shared atlas and stronghold aggregate repository."""
    return _west_marches_repo


def set_west_marches_repo(repo: AggregateRepository[WestMarchesAtlasAggregate]) -> None:
    """Set West Marches repository instance for testing."""
    global _west_marches_repo
    _west_marches_repo = repo


def set_spicedb_client(client: SpiceDBClient | MockSpiceDBClient | None) -> None:
    """Override SpiceDB client instance for testing."""
    global _spicedb_client
    _spicedb_client = client
