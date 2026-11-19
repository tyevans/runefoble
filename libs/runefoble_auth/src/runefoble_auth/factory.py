"""The single shared SpiceDB client factory for every bounded context and the gateway.

Settings come from `PlatformSettings`. The preshared key has no default (TASK-0625).
Tests swap the client with `set_spicedb_client` (TASK-0818). No caller keeps its own copy.
"""

from __future__ import annotations

from pydantic import ValidationError
from runefoble_platform.config import PlatformSettings
from runefoble_platform.errors import ConfigurationError

from runefoble_auth.mock.client import MockSpiceDBClient
from runefoble_auth.spicedb import SpiceDBClient

_client: SpiceDBClient | MockSpiceDBClient | None = None


def get_spicedb_client() -> SpiceDBClient:
    """Return the cached SpiceDB client, building it on first use.

    Raises:
        ConfigurationError: The preshared key or another required setting is missing.
    """
    global _client
    if _client is None:
        try:
            settings = PlatformSettings()
        except ValidationError as exc:
            raise ConfigurationError(
                "SpiceDB client settings are invalid. "
                "RUNEFOBLE_SPICEDB_PRESHARED_KEY is required and has no default. "
                f"{exc}"
            ) from exc
        _client = SpiceDBClient(
            endpoint=settings.spicedb_endpoint,
            token=settings.spicedb_preshared_key,
        )
    return _client


def set_spicedb_client(client: SpiceDBClient | MockSpiceDBClient | None) -> None:
    """Replace the shared client. Pass `None` to build a fresh one on the next call.

    Test seam only. Production code never calls it. Use `restored_seam` in tests to put back
    the previous client.
    """
    global _client
    _client = client
