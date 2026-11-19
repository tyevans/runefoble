"""Application service for multiplayer minigame tables (TASK-0566).

Loads the TavernGame aggregate for a table, runs one command, saves the new
events, and publishes them to the tavern stream. One lock serializes table
commands in this process so that load, decide, and save do not interleave.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any

from game_session.minigame_tables.models import MinigameTableState
from game_session.minigames import TavernGameAggregate
from game_session.shared.streams import STREAM_TAVERN
from runefoble_platform.aggregate_loading import load_if_exists
from runefoble_platform.event_bus import EventBusProvider
from runefoble_platform.event_publish import publish_aggregate_events
from runefoble_platform.event_sourcing import AggregateRepository
from runefoble_platform.identifiers import opaque_aggregate_id

_table_lock = asyncio.Lock()


class TableNotFoundError(LookupError):
    """No open table has this id."""


class TableAlreadyOpenError(ValueError):
    """A table with this id is already open."""


async def open_table(
    repo: AggregateRepository[TavernGameAggregate],
    event_bus: EventBusProvider,
    table_id: str,
    establishment_id: str,
    game_type: str,
) -> MinigameTableState:
    """Open a table. A table id is created only by this command, never by a socket connect."""
    async with _table_lock:
        table_uuid = opaque_aggregate_id(table_id, field="table_id")
        if await load_if_exists(repo, table_uuid) is not None:
            raise TableAlreadyOpenError(f"Table '{table_id}' is already open")
        aggregate = TavernGameAggregate(table_uuid)
        aggregate.open_table(table_id, establishment_id, game_type)
        events = list(aggregate.uncommitted_events)
        if events:
            await repo.save(aggregate)
            bus = event_bus.get()
            if bus:
                await publish_aggregate_events(bus, STREAM_TAVERN, events)
        return _table_of(aggregate, table_id)


async def load_table(
    repo: AggregateRepository[TavernGameAggregate], table_id: str
) -> MinigameTableState:
    """Read the current state of an open table."""
    aggregate = await load_if_exists(repo, opaque_aggregate_id(table_id, field="table_id"))
    if aggregate is None:
        raise TableNotFoundError(f"Table '{table_id}' is not open")
    return _table_of(aggregate, table_id)


async def run_table_command(
    repo: AggregateRepository[TavernGameAggregate],
    event_bus: EventBusProvider,
    table_id: str,
    command: Callable[[TavernGameAggregate], dict[str, Any]],
) -> dict[str, Any]:
    """Run one table command against the stored aggregate, then save and publish its events."""
    async with _table_lock:
        aggregate = await load_if_exists(repo, opaque_aggregate_id(table_id, field="table_id"))
        if aggregate is None:
            raise TableNotFoundError(f"Table '{table_id}' is not open")
        message = command(aggregate)
        events = list(aggregate.uncommitted_events)
        if events:
            await repo.save(aggregate)
            bus = event_bus.get()
            if bus:
                await publish_aggregate_events(bus, STREAM_TAVERN, events)
    return message


def _table_of(aggregate: TavernGameAggregate, table_id: str) -> MinigameTableState:
    table = aggregate.state.table
    if table is None:
        raise TableNotFoundError(f"Table '{table_id}' is not open")
    return table
