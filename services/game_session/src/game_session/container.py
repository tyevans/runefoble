"""Composition root of the game session service (ADR-0021 D6).

`build_container` reads the settings once and builds every repository and the event bus
provider. The app lifespan calls it at start-up and stores the result on
`app.state.container`. No module builds a repository or a client at import time.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from game_session.campaign.repositories import CampaignRepositories, build_campaign_repositories
from game_session.downtime.repositories import DowntimeRepositories, build_downtime_repositories
from game_session.play.repositories import PlayRepositories, build_play_repositories
from game_session.settlement.repositories import (
    SettlementRepositories,
    build_settlement_repositories,
)
from game_session.shared.child_index import ChildIndexAggregate
from game_session.shared.child_index_queries import build_child_index_repository
from game_session.world.repositories import WorldRepositories, build_world_repositories
from runefoble_auth.settings import load_spicedb_settings
from runefoble_platform.config import PlatformSettings
from runefoble_platform.event_bus import EventBusProvider
from runefoble_platform.event_sourcing import AggregateRepository, get_event_store


def watcher_service_url() -> str | None:
    """Return the configured Watcher base URL, or None when RUNEFOBLE_WATCHER_URL is unset."""
    return os.environ.get("RUNEFOBLE_WATCHER_URL", "").strip() or None


@dataclass(frozen=True)
class GameSessionContainer:
    """Every repository of the service, grouped by domain package, and the event bus."""

    event_bus: EventBusProvider
    child_indexes: AggregateRepository[ChildIndexAggregate]
    campaign: CampaignRepositories
    play: PlayRepositories
    downtime: DowntimeRepositories
    settlement: SettlementRepositories
    world: WorldRepositories


def build_container(
    settings: PlatformSettings | None = None, *, event_bus: EventBusProvider | None = None
) -> GameSessionContainer:
    """Build the container. Raise at start-up when a required setting is missing.

    - SpiceDB: this service checks permissions, so the preshared key is required (TASK-0720).
    - The Watcher: a deployed service must know its Watcher URL (ADR-0015 (4)).
    - The event store: build it now. A deployed service without a reachable PostgreSQL
      store, or with the memory store, refuses to start (ADR-0015 (f), TASK-0707).

    `event_bus` replaces the bus provider that the settings select. Tests pass one.
    """
    settings = settings if settings is not None else PlatformSettings()
    load_spicedb_settings()
    if settings.is_deployed and watcher_service_url() is None:
        raise RuntimeError(
            "RUNEFOBLE_WATCHER_URL must be set when RUNEFOBLE_ENVIRONMENT is "
            f"'{settings.environment}'"
        )
    get_event_store()
    bus = event_bus if event_bus is not None else EventBusProvider(settings)
    return GameSessionContainer(
        event_bus=bus,
        child_indexes=build_child_index_repository(),
        campaign=build_campaign_repositories(),
        play=build_play_repositories(bus),
        downtime=build_downtime_repositories(),
        settlement=build_settlement_repositories(),
        world=build_world_repositories(),
    )


__all__ = ["GameSessionContainer", "build_container", "watcher_service_url"]
