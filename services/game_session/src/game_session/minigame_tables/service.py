"""Application service for multiplayer minigame tables (TASK-0566).

Loads the TavernGame aggregate for a table, runs one command, saves the new
events, and publishes them to the tavern stream. One lock serializes table
commands in this process so that load, decide, and save do not interleave.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any

from eventsource import AggregateNotFoundError
from game_session.dependencies import get_event_bus, get_tavern_repository
from game_session.events import STREAM_TAVERN
from game_session.minigame_rules import to_uuid
from game_session.minigame_tables.models import MinigameTableState
from game_session.minigames import TavernGameAggregate
from runefoble_platform.event_publish import publish_or_fail

_table_lock = asyncio.Lock()


class TableNotFoundError(LookupError):
    """No open table has this id."""


class TableAlreadyOpenError(ValueError):
    """A table with this id is already open."""


async def open_table(table_id: str, establishment_id: str, game_type: str) -> MinigameTableState:
    """Open a table. A table id is created only by this command, never by a socket connect."""
    async with _table_lock:
        try:
            await get_tavern_repository().load(to_uuid(table_id))
        except AggregateNotFoundError:
            aggregate = TavernGameAggregate(to_uuid(table_id))
        else:
            raise TableAlreadyOpenError(f"Table '{table_id}' is already open")
        aggregate.open_table(table_id, establishment_id, game_type)
        await _save_and_publish(aggregate)
        return _table_of(aggregate, table_id)


async def load_table(table_id: str) -> MinigameTableState:
    """Read the current state of an open table."""
    try:
        aggregate = await get_tavern_repository().load(to_uuid(table_id))
    except AggregateNotFoundError as exc:
        raise TableNotFoundError(f"Table '{table_id}' is not open") from exc
    return _table_of(aggregate, table_id)


async def run_table_command(
    table_id: str,
    command: Callable[[TavernGameAggregate], dict[str, Any]],
) -> dict[str, Any]:
    """Run one table command against the stored aggregate, then save and publish its events."""
    async with _table_lock:
        try:
            aggregate = await get_tavern_repository().load(to_uuid(table_id))
        except AggregateNotFoundError as exc:
            raise TableNotFoundError(f"Table '{table_id}' is not open") from exc
        message = command(aggregate)
        await _save_and_publish(aggregate)
    return message


async def _save_and_publish(aggregate: TavernGameAggregate) -> None:
    events = list(aggregate.uncommitted_events)
    if not events:
        return
    await get_tavern_repository().save(aggregate)
    bus = get_event_bus()
    if bus:
        for event in events:
            await publish_or_fail(bus, STREAM_TAVERN, event)


def _table_of(aggregate: TavernGameAggregate, table_id: str) -> MinigameTableState:
    table = aggregate.state.table
    if table is None:
        raise TableNotFoundError(f"Table '{table_id}' is not open")
    return table
