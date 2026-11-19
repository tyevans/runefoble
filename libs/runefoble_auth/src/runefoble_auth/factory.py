"""The single shared SpiceDB client factory for every bounded context and the gateway.

Settings come from `SpiceDBSettings` (TASK-0720). The preshared key has no default (TASK-0625).
Tests swap the client with `set_spicedb_client` (TASK-0818). No caller keeps its own copy.
Callers type against `SpiceDBPort` (TASK-0911), never against a concrete client.
"""

from __future__ import annotations

from runefoble_auth.port import SpiceDBPort
from runefoble_auth.settings import load_spicedb_settings
from runefoble_auth.spicedb import SpiceDBClient

_client: SpiceDBPort | None = None


def get_spicedb_client() -> SpiceDBPort:
    """Return the cached SpiceDB client, building it on first use.

    Raises:
        ConfigurationError: The preshared key or another required setting is missing.
    """
    global _client
    if _client is None:
        settings = load_spicedb_settings()
        _client = SpiceDBClient(
            endpoint=settings.endpoint,
            token=settings.preshared_key.get_secret_value(),
        )
    return _client


def set_spicedb_client(client: SpiceDBPort | None) -> None:
    """Replace the shared client. Pass `None` to build a fresh one on the next call.

    Test seam only. Production code never calls it. Use `restored_seam` in tests to put back
    the previous client.
    """
    global _client
    _client = client
