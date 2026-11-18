"""Dependency injection and shared state for Campaign Lore service."""

from eventsource.domain.aggregate import DeclarativeAggregate
from eventsource.ports.store import FullEventStore
from fastapi import Request
from runefoble_platform.config import PlatformSettings
from runefoble_platform.errors import ServiceUnavailableError
from runefoble_platform.event_bus import EventBusProvider
from runefoble_platform.event_sourcing import (
    AggregateRepository,
    create_aggregate_repository,
    get_event_store,
)

from campaign_lore.aggregate import LoreDocumentAggregate
from campaign_lore.atlas_aggregate import AtlasAggregate
from campaign_lore.codex import CodexCrossReferencer
from campaign_lore.codex_aggregate import CodexAggregate
from campaign_lore.events import LoreEventPublisher
from campaign_lore.handouts_aggregate import DiegeticHandoutAggregate, RelicAggregate
from campaign_lore.retrieval import LoreRetrievalEngine
from campaign_lore.west_marches_aggregate import WestMarchesAtlasAggregate

# Fail fast at import when a required platform setting (the SpiceDB key) is missing (TASK-0625).
settings = PlatformSettings()

event_bus_provider = EventBusProvider(settings)
get_event_bus = event_bus_provider.get
set_event_bus = event_bus_provider.set

# Repositories are built per call from the active event store (see set_event_store),
# so a new application instance on the same store sees the same events. Each repository
# publishes its committed events to the lore streams through the configured bus.
_west_marches_repo_override: AggregateRepository[WestMarchesAtlasAggregate] | None = None


def _repo[T: DeclarativeAggregate](aggregate_factory: type[T]) -> AggregateRepository[T]:
    return create_aggregate_repository(
        aggregate_factory, event_bus=LoreEventPublisher(get_event_bus)
    )


def get_repo() -> AggregateRepository[LoreDocumentAggregate]:
    """Provide LoreDocument aggregate repository."""
    return _repo(LoreDocumentAggregate)


def get_handout_repo() -> AggregateRepository[DiegeticHandoutAggregate]:
    """Provide DiegeticHandout aggregate repository."""
    return _repo(DiegeticHandoutAggregate)


def get_relic_repo() -> AggregateRepository[RelicAggregate]:
    """Provide Relic aggregate repository."""
    return _repo(RelicAggregate)


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
    return _repo(AtlasAggregate)


def get_codex_repo() -> AggregateRepository[CodexAggregate]:
    """Provide Codex aggregate repository."""
    return _repo(CodexAggregate)


def get_codex_referencer(request: Request) -> CodexCrossReferencer:
    """Provide Codex cross-referencer bound to this application's retrieval engine."""
    referencer: CodexCrossReferencer = request.app.state.codex_referencer
    return referencer


def get_lore_event_store() -> FullEventStore:
    """Provide the event store that the codex list reads from."""
    return get_event_store()


def get_west_marches_repo() -> AggregateRepository[WestMarchesAtlasAggregate]:
    """Provide West Marches shared atlas and stronghold aggregate repository."""
    if _west_marches_repo_override is not None:
        return _west_marches_repo_override
    return _repo(WestMarchesAtlasAggregate)


def set_west_marches_repo(repo: AggregateRepository[WestMarchesAtlasAggregate] | None) -> None:
    """Override the West Marches repository instance for testing."""
    global _west_marches_repo_override
    _west_marches_repo_override = repo
