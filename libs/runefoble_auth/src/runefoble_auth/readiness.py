"""SpiceDB readiness probe for `runefoble_platform.readiness.ReadinessGate` (TASK-0930)."""

from __future__ import annotations

from runefoble_platform.readiness import ReadinessProbe

from runefoble_auth.factory import get_spicedb_client


def spicedb_probe() -> ReadinessProbe:
    """Probe SpiceDB with one schema read. The first call opens the gRPC channel.

    The probe reads the client through `get_spicedb_client` on each call, so it uses the same
    client as the permission checks.
    """

    async def probe() -> None:
        await get_spicedb_client().read_schema()

    return probe


__all__ = ["spicedb_probe"]
