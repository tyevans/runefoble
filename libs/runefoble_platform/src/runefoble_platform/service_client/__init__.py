"""Shared typed client for gateway calls to owning bounded contexts (TASK-0580)."""

from runefoble_platform.service_client.client import ServiceClient, UpstreamReply
from runefoble_platform.service_client.errors import (
    UpstreamError,
    UpstreamFailureError,
    UpstreamUnavailableError,
)
from runefoble_platform.service_client.health import ProbeStatus, probe_health
from runefoble_platform.service_client.paths import path

__all__ = [
    "ProbeStatus",
    "ServiceClient",
    "UpstreamError",
    "UpstreamFailureError",
    "UpstreamReply",
    "UpstreamUnavailableError",
    "path",
    "probe_health",
]
