"""Aggregate repositories of the downtime package (ADR-0021 D6 rule 5).

The app container holds one `DowntimeRepositories`. Routes read it through
`downtime_repositories`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends
from game_session.merchants import MerchantAggregate
from game_session.minigames import TavernGameAggregate
from game_session.shared.container_access import app_container
from game_session.stronghold import StrongholdAggregate
from runefoble_platform.event_sourcing import AggregateRepository, create_aggregate_repository
from starlette.requests import HTTPConnection


@dataclass(frozen=True)
class DowntimeRepositories:
    strongholds: AggregateRepository[StrongholdAggregate]
    tavern_games: AggregateRepository[TavernGameAggregate]
    merchants: AggregateRepository[MerchantAggregate]


def build_downtime_repositories() -> DowntimeRepositories:
    """Build the downtime repositories. Each resolves the event store per operation."""
    return DowntimeRepositories(
        strongholds=create_aggregate_repository(StrongholdAggregate),
        tavern_games=create_aggregate_repository(TavernGameAggregate),
        merchants=create_aggregate_repository(MerchantAggregate),
    )


def downtime_repositories(conn: HTTPConnection) -> DowntimeRepositories:
    """Return the downtime repositories of the app container."""
    return app_container(conn).downtime


DowntimeRepos = Annotated[DowntimeRepositories, Depends(downtime_repositories)]

__all__ = [
    "DowntimeRepos",
    "DowntimeRepositories",
    "build_downtime_repositories",
    "downtime_repositories",
]
