"""Shared dependencies, repository, and event bus for Game Session microservice."""

from __future__ import annotations

import contextlib
import logging
import os

from game_session.aggregate import GameSessionAggregate
from game_session.caravan import CaravanContractAggregate
from game_session.caravan_ledger import CaravanLedgerAggregate
from game_session.merchants import MerchantAggregate
from game_session.minigames import TavernGameAggregate
from game_session.settlements.aggregate import SettlementAggregate
from game_session.stronghold import StrongholdAggregate
from game_session.west_marches import SharedWorldAggregate
from runefoble_auth.spicedb import SpiceDBClient
from runefoble_platform.config import PlatformSettings
from runefoble_platform.event_sourcing import (
    AggregateRepository,
    create_aggregate_repository,
)
from runefoble_platform.redis_bus import RedisStreamsEventBus

logger = logging.getLogger("runefoble.game_session")
WATCHER_SERVICE_URL = os.environ.get("RUNEFOBLE_WATCHER_URL")
STREAM_WATCHER = "runefoble.events.watcher"
STREAM_SESSION = "runefoble.events.session"
STREAM_STRONGHOLD = "runefoble.events.stronghold"
STREAM_TAVERN = "runefoble.events.tavern"
STREAM_WEST_MARCHES = "runefoble.events.west_marches"

platform_settings = PlatformSettings()
_event_bus: RedisStreamsEventBus | None = None
_spicedb_client: SpiceDBClient = SpiceDBClient()

repo: AggregateRepository[GameSessionAggregate] = create_aggregate_repository(GameSessionAggregate)
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


def get_tavern_repository() -> AggregateRepository[TavernGameAggregate]:
    return tavern_repo


def get_merchant_repository() -> AggregateRepository[MerchantAggregate]:
    return merchant_repo


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


_world_contracts_index: dict[str, list[str]] = {}


def get_world_contracts_index() -> dict[str, list[str]]:
    return _world_contracts_index


def get_spicedb_client() -> SpiceDBClient:
    return _spicedb_client


def set_spicedb_client(client: SpiceDBClient) -> None:
    global _spicedb_client
    _spicedb_client = client


def get_event_bus() -> RedisStreamsEventBus | None:
    global _event_bus
    if _event_bus is None and platform_settings.redis_url:
        with contextlib.suppress(Exception):
            _event_bus = RedisStreamsEventBus(redis_url=platform_settings.redis_url)
    return _event_bus


def set_event_bus(bus: RedisStreamsEventBus | None) -> None:
    global _event_bus
    _event_bus = bus
