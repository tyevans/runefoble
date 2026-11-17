"""Shared typed client for gateway calls to owning bounded contexts (TASK-0580)."""

from runefoble_platform.service_client.client import ServiceClient, UpstreamReply
from runefoble_platform.service_client.errors import (
    UpstreamError,
    UpstreamFailureError,
    UpstreamUnavailableError,
)

__all__ = [
    "ServiceClient",
    "UpstreamError",
    "UpstreamFailureError",
    "UpstreamReply",
    "UpstreamUnavailableError",
]
