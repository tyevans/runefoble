"""Shared dependencies, engine instances, and event bus for The Watcher service."""

from __future__ import annotations

import logging
import os
from uuid import NAMESPACE_DNS, UUID, uuid4, uuid5

from runefoble_auth.spicedb import MockSpiceDBClient, SpiceDBClient
from runefoble_platform.config import PlatformSettings
from runefoble_platform.event_sourcing import (
    AggregateRepository,
    create_aggregate_repository,
)
from runefoble_platform.redis_bus import RedisStreamsEventBus
from the_watcher.autonomous_dm import AutonomousDMEngine
from the_watcher.chronicle import ChronicleRecapEngine
from the_watcher.compound_actions import CompoundActionEngine
from the_watcher.copilot import CopilotEngine
from the_watcher.disambiguation import DisambiguationEngine
from the_watcher.factions import FactionAggregate
from the_watcher.factions.resources import FactionResourceAggregate
from the_watcher.simulation_engine import FactionSimulationEngine
from the_watcher.turf_war.aggregate import RegionalUnrestAggregate
from the_watcher.watcher_ai import TheWatcherEngine

logger = logging.getLogger("runefoble.the_watcher")
INFERENCE_URL = os.environ.get("RUNEFOBLE_INFERENCE_URL")

STREAM_WATCHER = "runefoble.events.watcher"
STREAM_BOARD = "runefoble.events.board"
STREAM_WORLD = "runefoble:events:world"

engine = TheWatcherEngine()
chronicle_engine = ChronicleRecapEngine()
autonomous_dm_engine = AutonomousDMEngine()
copilot_engine = CopilotEngine()
disambiguation_engine = DisambiguationEngine()
compound_action_engine = CompoundActionEngine()
faction_simulation_engine = FactionSimulationEngine()

platform_settings = PlatformSettings()

_event_bus: RedisStreamsEventBus | None = None
_spicedb_client: SpiceDBClient | MockSpiceDBClient | None = None
_faction_repo: AggregateRepository[FactionAggregate] | None = None
_faction_resource_repo: AggregateRepository[FactionResourceAggregate] | None = None
_regional_unrest_repo: AggregateRepository[RegionalUnrestAggregate] | None = None


def get_spicedb_client() -> SpiceDBClient | MockSpiceDBClient:
    global _spicedb_client
    if _spicedb_client is None:
        _spicedb_client = SpiceDBClient(
            endpoint=platform_settings.spicedb_endpoint,
            token=platform_settings.spicedb_token,
        )
    return _spicedb_client


def set_spicedb_client(client: SpiceDBClient | MockSpiceDBClient | None) -> None:
    global _spicedb_client
    _spicedb_client = client


def get_copilot_engine() -> CopilotEngine:
    return copilot_engine


def get_faction_simulation_engine() -> FactionSimulationEngine:
    return faction_simulation_engine


def get_faction_repo() -> AggregateRepository[FactionAggregate]:
    global _faction_repo
    if _faction_repo is None:
        _faction_repo = create_aggregate_repository(FactionAggregate)
    return _faction_repo


def set_faction_repo(repo: AggregateRepository[FactionAggregate] | None) -> None:
    global _faction_repo
    _faction_repo = repo


def get_faction_resource_repo() -> AggregateRepository[FactionResourceAggregate]:
    global _faction_resource_repo
    if _faction_resource_repo is None:
        _faction_resource_repo = create_aggregate_repository(FactionResourceAggregate)
    return _faction_resource_repo


def set_faction_resource_repo(repo: AggregateRepository[FactionResourceAggregate] | None) -> None:
    global _faction_resource_repo
    _faction_resource_repo = repo


def get_regional_unrest_repo() -> AggregateRepository[RegionalUnrestAggregate]:
    global _regional_unrest_repo
    if _regional_unrest_repo is None:
        _regional_unrest_repo = create_aggregate_repository(RegionalUnrestAggregate)
    return _regional_unrest_repo


def set_regional_unrest_repo(repo: AggregateRepository[RegionalUnrestAggregate] | None) -> None:
    global _regional_unrest_repo
    _regional_unrest_repo = repo


async def check_dm_authorization(
    user_id: str | None,
    campaign_id: str | None = None,
    session_id: str | None = None,
    spicedb: SpiceDBClient | MockSpiceDBClient | None = None,
) -> bool:
    """Check Zanzibar authorization for DM actions (veto, approve, modify, whispers)."""
    if not user_id:
        return False
    client = spicedb or get_spicedb_client()

    target_campaign = campaign_id
    if not target_campaign and session_id:
        target_campaign = session_id

    if target_campaign:
        if await client.check_permission(
            "campaign", str(target_campaign), "dungeon_master", "user", user_id
        ):
            return True
        if await client.check_permission(
            "campaign", str(target_campaign), "run_session", "user", user_id
        ):
            return True
        if await client.check_permission(
            "campaign", str(target_campaign), "owner", "user", user_id
        ):
            return True

    if session_id:
        if await client.check_permission("session", str(session_id), "control", "user", user_id):
            return True
        if await client.check_permission(
            "session", str(session_id), "run_session", "user", user_id
        ):
            return True
        if await client.check_permission(
            "session", str(session_id), "dungeon_master", "user", user_id
        ):
            return True

    return False


def get_event_bus() -> RedisStreamsEventBus:
    global _event_bus
    if _event_bus is None:
        _event_bus = RedisStreamsEventBus(redis_url=platform_settings.redis_url)
    return _event_bus


def set_event_bus(bus: RedisStreamsEventBus | None) -> None:
    global _event_bus
    _event_bus = bus


def to_uuid(val: str | UUID | None) -> UUID:
    """Deterministically convert a string or UUID into a valid UUID."""
    if val is None:
        return uuid4()
    if isinstance(val, UUID):
        return val
    try:
        return UUID(val)
    except ValueError:
        return uuid5(NAMESPACE_DNS, str(val))
