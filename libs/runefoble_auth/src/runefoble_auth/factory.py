"""The single shared SpiceDB client factory for every bounded context and the gateway.

Settings come from `PlatformSettings`. The preshared key has no default (TASK-0625).
"""

from __future__ import annotations

from pydantic import ValidationError
from runefoble_platform.config import PlatformSettings
from runefoble_platform.errors import ConfigurationError

from runefoble_auth.spicedb import SpiceDBClient

_client: SpiceDBClient | None = None


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
