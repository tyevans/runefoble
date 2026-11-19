"""Aggregate repositories of the settlement package (ADR-0021 D6 rule 5).

The app container holds one `SettlementRepositories`. Routes read it through
`settlement_repositories`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends
from game_session.settlement.establishment_aggregate import EstablishmentAggregate
from game_session.settlement.haggling import NegotiationAggregate
from game_session.settlement.settlement_aggregate import SettlementAggregate
from game_session.settlement.workers import NPCWorkerAggregate
from game_session.shared.container_access import app_container
from runefoble_platform.event_sourcing import AggregateRepository, create_aggregate_repository
from starlette.requests import HTTPConnection


@dataclass(frozen=True)
class SettlementRepositories:
    settlements: AggregateRepository[SettlementAggregate]
    establishments: AggregateRepository[EstablishmentAggregate]
    workers: AggregateRepository[NPCWorkerAggregate]
    negotiations: AggregateRepository[NegotiationAggregate]


def build_settlement_repositories() -> SettlementRepositories:
    """Build the settlement repositories. Each resolves the event store per operation."""
    return SettlementRepositories(
        settlements=create_aggregate_repository(SettlementAggregate),
        establishments=create_aggregate_repository(EstablishmentAggregate),
        workers=create_aggregate_repository(NPCWorkerAggregate),
        negotiations=create_aggregate_repository(NegotiationAggregate),
    )


def settlement_repositories(conn: HTTPConnection) -> SettlementRepositories:
    """Return the settlement repositories of the app container."""
    return app_container(conn).settlement


SettlementRepos = Annotated[SettlementRepositories, Depends(settlement_repositories)]

__all__ = [
    "SettlementRepos",
    "SettlementRepositories",
    "build_settlement_repositories",
    "settlement_repositories",
]
