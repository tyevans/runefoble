"""Readiness gate: a service is ready only after each dependency answered once (TASK-0929).

A Kubernetes readiness probe calls `GET /readyz`. The gate runs one probe for each
dependency that has not answered yet (for example the event store, SpiceDB and Redis).
The probes run at the same time, each with a time limit. A probe that answers is not run
again, so `/readyz` costs nothing after the warm-up. `/healthz` stays the cheap liveness
check.

A failed probe is logged at warning level with the dependency name and the error, and
`/readyz` answers 503 with the same detail (ADR-0015: failures are visible).
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable, Mapping

from fastapi import FastAPI
from fastapi.responses import JSONResponse

logger = logging.getLogger("runefoble.readiness")

ReadinessProbe = Callable[[], Awaitable[object]]

DEFAULT_PROBE_TIMEOUT_S = 2.5


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


def add_readiness_route(app: FastAPI, service: str, gate: ReadinessGate) -> None:
    """Add `GET /readyz`: 200 when every dependency answered once, else 503 with the failures."""

    async def readiness() -> JSONResponse:
        failures = await gate.pending()
        if failures:
            return JSONResponse(
                status_code=503,
                content={"status": "not_ready", "service": service, "pending": failures},
            )
        return JSONResponse(status_code=200, content={"status": "ready", "service": service})

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
]
