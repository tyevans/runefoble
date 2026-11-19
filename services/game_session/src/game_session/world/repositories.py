"""Aggregate repositories of the world package (ADR-0021 D6 rule 5).

The app container holds one `WorldRepositories`. Routes read it through `world_repositories`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends
from game_session.caravan import CaravanContractAggregate
from game_session.caravan.ledger import CaravanLedgerAggregate
from game_session.contracts.engine import MercenaryBountyAggregate
from game_session.shared.container_access import app_container
from game_session.west_marches import SharedWorldAggregate
from runefoble_platform.event_sourcing import AggregateRepository, create_aggregate_repository
from starlette.requests import HTTPConnection


@dataclass(frozen=True)
class WorldRepositories:
    shared_worlds: AggregateRepository[SharedWorldAggregate]
    caravan_ledgers: AggregateRepository[CaravanLedgerAggregate]
    caravan_contracts: AggregateRepository[CaravanContractAggregate]
    bounty_contracts: AggregateRepository[MercenaryBountyAggregate]


def build_world_repositories() -> WorldRepositories:
    """Build the world repositories. Each resolves the event store per operation."""
    return WorldRepositories(
        shared_worlds=create_aggregate_repository(SharedWorldAggregate),
        caravan_ledgers=create_aggregate_repository(CaravanLedgerAggregate),
        caravan_contracts=create_aggregate_repository(CaravanContractAggregate),
        bounty_contracts=create_aggregate_repository(MercenaryBountyAggregate),
    )


def world_repositories(conn: HTTPConnection) -> WorldRepositories:
    """Return the world repositories of the app container."""
    return app_container(conn).world


WorldRepos = Annotated[WorldRepositories, Depends(world_repositories)]

__all__ = ["WorldRepos", "WorldRepositories", "build_world_repositories", "world_repositories"]
