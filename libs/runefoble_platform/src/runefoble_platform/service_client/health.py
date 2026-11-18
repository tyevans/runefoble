"""Probe the health of one owning service through the shared service client (TASK-0674).

A probe sends a real `GET /healthz` request. Results are never cached. The caller reports
the status name in its own health response.
"""

from __future__ import annotations

from enum import StrEnum

from runefoble_platform.service_client.client import ServiceClient
from runefoble_platform.service_client.errors import (
    UpstreamFailureError,
    UpstreamUnavailableError,
)

HEALTH_PATH = "/healthz"
OPERATIONAL_STATUS_CODE = 200


class ProbeStatus(StrEnum):
    """The status of one owning service, as a health report shows it."""

    OPERATIONAL = "operational"
    DEGRADED = "degraded"
    UNREACHABLE = "unreachable"
    NOT_CONFIGURED = "not_configured"


async def probe_health(client: ServiceClient | None, *, timeout_s: float) -> ProbeStatus:
    """Probe one service and return its status.

    `client` is None when no base URL is configured. HTTP 200 is operational. Any other
    HTTP status is degraded. A timeout or a connection error is unreachable.
    """
    if client is None:
        return ProbeStatus.NOT_CONFIGURED
    try:
        reply = await client.send("GET", HEALTH_PATH, authorization=None, timeout_s=timeout_s)
    except UpstreamUnavailableError:
        return ProbeStatus.UNREACHABLE
    except UpstreamFailureError:
        return ProbeStatus.DEGRADED
    if reply.status_code == OPERATIONAL_STATUS_CODE:
        return ProbeStatus.OPERATIONAL
    return ProbeStatus.DEGRADED
