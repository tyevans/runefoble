"""Shared dependencies, repository, and event bus for Game Session microservice."""

from __future__ import annotations

import logging
import os

from game_session.aggregate import GameSessionAggregate
from game_session.caravan import CaravanContractAggregate
from game_session.caravan.ledger import CaravanLedgerAggregate
from game_session.child_index import ChildIndexAggregate
from game_session.contracts.engine import MercenaryBountyAggregate
from game_session.events import SessionEventPublisher
from game_session.merchants import MerchantAggregate
from game_session.minigames import TavernGameAggregate
from game_session.settlement.establishment_aggregate import EstablishmentAggregate
from game_session.settlement.haggling import NegotiationAggregate
from game_session.settlement.settlement_aggregate import SettlementAggregate
from game_session.settlement.workers import NPCWorkerAggregate
from game_session.stronghold import StrongholdAggregate
from game_session.west_marches import SharedWorldAggregate
from runefoble_auth.spicedb import MockSpiceDBClient, SpiceDBClient
from runefoble_platform.config import PlatformSettings
from runefoble_platform.event_bus import EventBusProvider
from runefoble_platform.event_sourcing import (
    AggregateRepository,
    create_aggregate_repository,
)

logger = logging.getLogger("runefoble.game_session")


def watcher_service_url() -> str | None:
    """Return the configured Watcher base URL, or None when RUNEFOBLE_WATCHER_URL is unset."""
    return os.environ.get("RUNEFOBLE_WATCHER_URL", "").strip() or None


platform_settings = PlatformSettings()
if platform_settings.is_deployed and watcher_service_url() is None:
    # ADR-0015 (4): a deployed session service must not start without its Watcher.
    raise RuntimeError(
        "RUNEFOBLE_WATCHER_URL must be set when RUNEFOBLE_ENVIRONMENT is "
        f"'{platform_settings.environment}'"
    )
_spicedb_client: SpiceDBClient | MockSpiceDBClient | None = None

repo: AggregateRepository[GameSessionAggregate] = create_aggregate_repository(
    GameSessionAggregate,
    event_bus=SessionEventPublisher(lambda: get_event_bus()),
)
stronghold_repo: AggregateRepository[StrongholdAggregate] = create_aggregate_repository(
    StrongholdAggregate
)
tavern_repo: AggregateRepository[TavernGameAggregate] = create_aggregate_repository(
    TavernGameAggregate
)
merchant_repo: AggregateRepository[MerchantAggregate] = create_aggregate_repository(
    MerchantAggregate
)

shared_world_repo: AggregateRepository[SharedWorldAggregate] = create_aggregate_repository(
    SharedWorldAggregate
)
caravan_ledger_repo: AggregateRepository[CaravanLedgerAggregate] = create_aggregate_repository(
    CaravanLedgerAggregate
)
caravan_contract_repo: AggregateRepository[CaravanContractAggregate] = create_aggregate_repository(
    CaravanContractAggregate
)
settlement_repo: AggregateRepository[SettlementAggregate] = create_aggregate_repository(
    SettlementAggregate
)
establishment_repo: AggregateRepository[EstablishmentAggregate] = create_aggregate_repository(
    EstablishmentAggregate
)
bounty_contract_repo: AggregateRepository[MercenaryBountyAggregate] = create_aggregate_repository(
    MercenaryBountyAggregate
)
worker_repo: AggregateRepository[NPCWorkerAggregate] = create_aggregate_repository(
    NPCWorkerAggregate
)
negotiation_repo: AggregateRepository[NegotiationAggregate] = create_aggregate_repository(
    NegotiationAggregate
)
child_index_repo: AggregateRepository[ChildIndexAggregate] = create_aggregate_repository(
    ChildIndexAggregate
)


def get_tavern_repository() -> AggregateRepository[TavernGameAggregate]:
    return tavern_repo


def get_merchant_repository() -> AggregateRepository[MerchantAggregate]:
    return merchant_repo


def get_negotiation_repository() -> AggregateRepository[NegotiationAggregate]:
    return negotiation_repo


def get_stronghold_repository() -> AggregateRepository[StrongholdAggregate]:
    return stronghold_repo


def get_shared_world_repository() -> AggregateRepository[SharedWorldAggregate]:
    return shared_world_repo


def get_caravan_ledger_repository() -> AggregateRepository[CaravanLedgerAggregate]:
    return caravan_ledger_repo


def get_caravan_contract_repository() -> AggregateRepository[CaravanContractAggregate]:
    return caravan_contract_repo


def get_settlement_repository() -> AggregateRepository[SettlementAggregate]:
    return settlement_repo


def get_establishment_repository() -> AggregateRepository[EstablishmentAggregate]:
    return establishment_repo


def get_bounty_contract_repository() -> AggregateRepository[MercenaryBountyAggregate]:
    return bounty_contract_repo


def get_worker_repository() -> AggregateRepository[NPCWorkerAggregate]:
    return worker_repo


def get_child_index_repository() -> AggregateRepository[ChildIndexAggregate]:
    return child_index_repo


def get_spicedb_client() -> SpiceDBClient | MockSpiceDBClient:
    global _spicedb_client
    if _spicedb_client is None:
        _spicedb_client = SpiceDBClient()
    return _spicedb_client


def set_spicedb_client(client: SpiceDBClient | MockSpiceDBClient | None) -> None:
    global _spicedb_client
    _spicedb_client = client


event_bus_provider = EventBusProvider(platform_settings)
get_event_bus = event_bus_provider.get
set_event_bus = event_bus_provider.set
