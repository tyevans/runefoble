"""Readiness gate: a service is ready only after each dependency answered once (TASK-0929, 0930).

A Kubernetes readiness probe calls `GET /readyz`. The gate runs one probe for each
dependency that has not answered yet (for example the event store, SpiceDB and Redis).
The probes run at the same time, each with a time limit. A probe that answers is not run
again, so `/readyz` costs nothing after the warm-up. `/healthz` stays the cheap liveness
check.

A failed probe is logged at warning level with the dependency name and the error, and
`/readyz` answers 503 with the same detail (ADR-0015: failures are visible).

`event_store_probe`, `redis_probe` and `silo_probe` are the shared probes. A service registers only the
dependencies that it uses (`runefoble_auth.readiness.spicedb_probe` for SpiceDB).
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable, Mapping
from uuid import UUID

from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import JSONResponse

from runefoble_platform.event_sourcing import get_event_store
from runefoble_platform.redis_bus import RedisStreamsEventBus
from runefoble_platform.storage import get_storage_service

logger = logging.getLogger("runefoble.readiness")

ReadinessProbe = Callable[[], Awaitable[object]]

DEFAULT_PROBE_TIMEOUT_S = 2.5

_PROBE_EVENT_ID = UUID(int=0)


def event_store_probe() -> ReadinessProbe:
    """Probe the event store. The first call opens the pool and runs the schema check.

    The probe reads the store through `get_event_store` on each call, so it uses the same
    store as the routes.
    """

    async def probe() -> None:
        await get_event_store().event_exists(_PROBE_EVENT_ID)

    return probe


def redis_probe(bus: Callable[[], RedisStreamsEventBus]) -> ReadinessProbe:
    """Probe Redis with one PING on the bus that `bus()` returns (the service event bus)."""

    async def probe() -> None:
        client = await bus().get_client()
        await client.ping()

    return probe


def silo_probe() -> ReadinessProbe:
    """Probe Silo with one signed HEAD on the default asset bucket.

    The probe reads the client through `get_storage_service` on each call, so it uses the
    same client as the upload routes. The client is synchronous, so the call runs in a thread.
    """

    async def probe() -> None:
        await asyncio.to_thread(get_storage_service().check_bucket)

    return probe


class ReadinessGate:
    """Track which dependencies have answered once. Probe only those that have not."""

    def __init__(
        self,
        probes: Mapping[str, ReadinessProbe],
        *,
        timeout_s: float = DEFAULT_PROBE_TIMEOUT_S,
    ) -> None:
        self._probes = dict(probes)
        self._timeout_s = timeout_s
        self._answered: set[str] = set()

    async def pending(self) -> dict[str, str]:
        """Probe each dependency that has not answered. Return the failures by name."""
        names = [name for name in self._probes if name not in self._answered]
        results = await asyncio.gather(*(self._probe(name) for name in names))
        return {name: error for name, error in zip(names, results, strict=True) if error}

    async def _probe(self, name: str) -> str | None:
        try:
            await asyncio.wait_for(self._probes[name](), timeout=self._timeout_s)
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}" if str(exc) else type(exc).__name__
            logger.warning("Readiness probe %s failed: %s", name, error)
            return error
        self._answered.add(name)
        logger.info("Readiness probe %s answered", name)
        return None


def set_readiness_gate(app: FastAPI, gate: ReadinessGate) -> None:
    """Make `gate` the gate that `/readyz` of `app` uses. Call it at the start of the lifespan.

    A new lifespan gets a new gate, so no dependency counts as answered before the app starts.
    """
    app.state.readiness_gate = gate


async def readiness_response(gate: ReadinessGate, service: str) -> JSONResponse:
    """Answer 200 when every dependency answered once, else 503 with the failures by name.

    Services whose router is not a FastAPI router (for example a FastMCP app) use this function
    with their own route. `add_readiness_route` uses it too.
    """
    failures = await gate.pending()
    if failures:
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "service": service, "pending": failures},
        )
    return JSONResponse(status_code=200, content={"status": "ready", "service": service})


def add_readiness_route(app: FastAPI | APIRouter, service: str) -> None:
    """Add `GET /readyz`: 200 when every dependency answered once, else 503 with the failures.

    `app` is the app or the router that owns the health routes of the service. The route uses
    the gate that the lifespan set with `set_readiness_gate`.
    """

    async def readiness(request: Request) -> JSONResponse:
        gate: ReadinessGate = request.app.state.readiness_gate
        return await readiness_response(gate, service)

    app.add_api_route(
        "/readyz",
        readiness,
        methods=["GET"],
        summary="Report ready when every dependency answered once",
        response_model=None,
    )


__all__ = [
    "DEFAULT_PROBE_TIMEOUT_S",
    "ReadinessGate",
    "ReadinessProbe",
    "add_readiness_route",
    "event_store_probe",
    "readiness_response",
    "redis_probe",
    "set_readiness_gate",
    "silo_probe",
]
