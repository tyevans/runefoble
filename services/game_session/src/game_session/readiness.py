"""Readiness probes of the game session service (TASK-0929).

A write route needs the event store, SpiceDB and Redis. Each probe makes one cheap call
through the same client that the routes use, so the first call after start-up (connection
pool, schema check, gRPC channel) happens in the probe and not in a player's request.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import FastAPI
from runefoble_auth.factory import get_spicedb_client
from runefoble_platform.event_sourcing import get_event_store
from runefoble_platform.readiness import ReadinessGate

_PROBE_EVENT_ID = UUID(int=0)


def build_readiness_gate(app: FastAPI) -> ReadinessGate:
    """Return the gate for `app`. The Redis probe reads the bus from `app.state.container`."""

    async def event_store() -> None:
        await get_event_store().event_exists(_PROBE_EVENT_ID)

    async def spicedb() -> None:
        await get_spicedb_client().read_schema()

    async def redis() -> None:
        client = await app.state.container.event_bus.get().get_client()
        await client.ping()

    return ReadinessGate({"event_store": event_store, "spicedb": spicedb, "redis": redis})


__all__ = ["build_readiness_gate"]
