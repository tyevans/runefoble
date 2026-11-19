"""Shared typed client for gateway calls to owning bounded contexts (TASK-0580, TASK-0822)."""

from runefoble_platform.service_client.client import ServiceClient, UpstreamReply
from runefoble_platform.service_client.errors import (
    UpstreamError,
    UpstreamFailureError,
    UpstreamUnavailableError,
)
from runefoble_platform.service_client.health import ProbeStatus, probe_health
from runefoble_platform.service_client.owner_routes import OwnerRoute
from runefoble_platform.service_client.owners import OWNER_URL_FIELDS
from runefoble_platform.service_client.paths import path
from runefoble_platform.service_client.replies import decode_json_body, error_detail

__all__ = [
    "OWNER_URL_FIELDS",
    "OwnerRoute",
    "ProbeStatus",
    "ServiceClient",
    "UpstreamError",
    "UpstreamFailureError",
    "UpstreamReply",
    "UpstreamUnavailableError",
    "decode_json_body",
    "error_detail",
    "path",
    "probe_health",
]
