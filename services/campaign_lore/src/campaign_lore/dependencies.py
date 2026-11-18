"""Dependency injection and shared state for Campaign Lore service."""

from uuid import UUID

from fastapi import Request
from runefoble_platform.config import PlatformSettings
from runefoble_platform.errors import ServiceUnavailableError
from runefoble_platform.event_sourcing import AggregateRepository, create_aggregate_repository

from campaign_lore.aggregate import LoreDocumentAggregate
from campaign_lore.atlas_aggregate import AtlasAggregate
from campaign_lore.codex import CodexCrossReferencer
from campaign_lore.codex_aggregate import CodexAggregate
from campaign_lore.handouts_aggregate import DiegeticHandoutAggregate, RelicAggregate
from campaign_lore.retrieval import LoreRetrievalEngine
from campaign_lore.west_marches_aggregate import WestMarchesAtlasAggregate

# Fail fast at import when a required platform setting (the SpiceDB key) is missing (TASK-0625).
settings = PlatformSettings()

# Repositories are built per call from the active event store (see set_event_store),
# so a new application instance on the same store sees the same events.
_campaign_codex_entries: dict[UUID, list[UUID]] = {}
_west_marches_repo_override: AggregateRepository[WestMarchesAtlasAggregate] | None = None


def get_repo() -> AggregateRepository[LoreDocumentAggregate]:
    """Provide LoreDocument aggregate repository."""
    return create_aggregate_repository(LoreDocumentAggregate)


def get_handout_repo() -> AggregateRepository[DiegeticHandoutAggregate]:
    """Provide DiegeticHandout aggregate repository."""
    return create_aggregate_repository(DiegeticHandoutAggregate)


def get_relic_repo() -> AggregateRepository[RelicAggregate]:
    """Provide Relic aggregate repository."""
    return create_aggregate_repository(RelicAggregate)


def get_retrieval_engine(request: Request) -> LoreRetrievalEngine:
    """Provide the retrieval engine owned by this application instance.

    The engine exists only after the application lifespan has started. A missing engine is
    a service that is not ready, so the request fails with 503 instead of an AttributeError.
    """
    engine: LoreRetrievalEngine | None = getattr(request.app.state, "retrieval_engine", None)
    if engine is None:
        raise ServiceUnavailableError("campaign_lore is not started")
    return engine


def get_atlas_repo() -> AggregateRepository[AtlasAggregate]:
    """Provide Atlas aggregate repository."""
    return create_aggregate_repository(AtlasAggregate)


def get_codex_repo() -> AggregateRepository[CodexAggregate]:
    """Provide Codex aggregate repository."""
    return create_aggregate_repository(CodexAggregate)


def get_codex_referencer(request: Request) -> CodexCrossReferencer:
    """Provide Codex cross-referencer bound to this application's retrieval engine."""
    referencer: CodexCrossReferencer = request.app.state.codex_referencer
    return referencer


def get_campaign_codex_index() -> dict[UUID, list[UUID]]:
    """Provide in-memory campaign codex entry index."""
    return _campaign_codex_entries


def get_west_marches_repo() -> AggregateRepository[WestMarchesAtlasAggregate]:
    """Provide West Marches shared atlas and stronghold aggregate repository."""
    if _west_marches_repo_override is not None:
        return _west_marches_repo_override
    return create_aggregate_repository(WestMarchesAtlasAggregate)


def set_west_marches_repo(repo: AggregateRepository[WestMarchesAtlasAggregate] | None) -> None:
    """Override the West Marches repository instance for testing."""
    global _west_marches_repo_override
    _west_marches_repo_override = repo
