"""TCP port probing and the Redis endpoint that the services use."""

from __future__ import annotations

import socket
from collections.abc import Mapping
from urllib.parse import urlparse

DEFAULT_REDIS_URL = "redis://localhost:6379/0"


def is_port_open(host: str, port: int, timeout: float = 0.5) -> bool:
    """Check if a TCP port is open and accepting connections."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def redis_endpoint(env: Mapping[str, str]) -> tuple[str, int]:
    """Return the Redis host and port that services will use, from the same env as the gateway."""
    url = env.get("RUNEFOBLE_REDIS_URL") or DEFAULT_REDIS_URL
    parsed = urlparse(url)
    return parsed.hostname or "localhost", parsed.port or 6379
