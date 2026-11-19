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
from runefoble_platform.config import PlatformSettings
from runefoble_platform.event_bus import EventBusProvider
from runefoble_platform.event_sourcing import (
    AggregateRepository,
    create_aggregate_repository,
)
from runefoble_platform.lazy_repository import LazyRepository

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

repo: AggregateRepository[GameSessionAggregate] = create_aggregate_repository(
    GameSessionAggregate,
    event_bus=SessionEventPublisher(lambda: get_event_bus()),
)
stronghold_repository = LazyRepository(lambda: create_aggregate_repository(StrongholdAggregate))
tavern_repository = LazyRepository(lambda: create_aggregate_repository(TavernGameAggregate))
merchant_repository = LazyRepository(lambda: create_aggregate_repository(MerchantAggregate))
shared_world_repository = LazyRepository(lambda: create_aggregate_repository(SharedWorldAggregate))
caravan_ledger_repository = LazyRepository(
    lambda: create_aggregate_repository(CaravanLedgerAggregate)
)
caravan_contract_repository = LazyRepository(
    lambda: create_aggregate_repository(CaravanContractAggregate)
)
settlement_repository = LazyRepository(lambda: create_aggregate_repository(SettlementAggregate))
establishment_repository = LazyRepository(
    lambda: create_aggregate_repository(EstablishmentAggregate)
)
bounty_contract_repository = LazyRepository(
    lambda: create_aggregate_repository(MercenaryBountyAggregate)
)
worker_repository = LazyRepository(lambda: create_aggregate_repository(NPCWorkerAggregate))
negotiation_repository = LazyRepository(lambda: create_aggregate_repository(NegotiationAggregate))
child_index_repository = LazyRepository(lambda: create_aggregate_repository(ChildIndexAggregate))


def get_game_session_repository() -> AggregateRepository[GameSessionAggregate]:
    return repo


def get_stronghold_repository() -> AggregateRepository[StrongholdAggregate]:
    return stronghold_repository.get()


def get_tavern_repository() -> AggregateRepository[TavernGameAggregate]:
    return tavern_repository.get()


def get_merchant_repository() -> AggregateRepository[MerchantAggregate]:
    return merchant_repository.get()


def get_shared_world_repository() -> AggregateRepository[SharedWorldAggregate]:
    return shared_world_repository.get()


def get_caravan_ledger_repository() -> AggregateRepository[CaravanLedgerAggregate]:
    return caravan_ledger_repository.get()


def get_caravan_contract_repository() -> AggregateRepository[CaravanContractAggregate]:
    return caravan_contract_repository.get()


def get_settlement_repository() -> AggregateRepository[SettlementAggregate]:
    return settlement_repository.get()


def get_establishment_repository() -> AggregateRepository[EstablishmentAggregate]:
    return establishment_repository.get()


def get_bounty_contract_repository() -> AggregateRepository[MercenaryBountyAggregate]:
    return bounty_contract_repository.get()


def get_worker_repository() -> AggregateRepository[NPCWorkerAggregate]:
    return worker_repository.get()


def get_negotiation_repository() -> AggregateRepository[NegotiationAggregate]:
    return negotiation_repository.get()


def get_child_index_repository() -> AggregateRepository[ChildIndexAggregate]:
    return child_index_repository.get()


event_bus_provider = EventBusProvider(platform_settings)
get_event_bus = event_bus_provider.get
set_event_bus = event_bus_provider.set
