"""SpiceDB connection settings (TASK-0720).

Only processes that talk to SpiceDB build these settings. `PlatformSettings` does not hold
them, so a service that never checks a permission starts without the preshared key.

Governed by:
- ADR-0001: SpiceDB Zanzibar Object Authorization (the key is an operator secret)
- ADR-0015: Audit Remediation Decisions (no literal default for the key)
"""

from __future__ import annotations

from pydantic import AliasChoices, Field, SecretStr, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict
from runefoble_platform.errors import ConfigurationError

PRESHARED_KEY_VAR = "RUNEFOBLE_SPICEDB_PRESHARED_KEY"
ENDPOINT_VAR = "RUNEFOBLE_SPICEDB_ENDPOINT"


class SpiceDBSettings(BaseSettings):
    """The SpiceDB gRPC endpoint and preshared key. The key has no default."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    endpoint: str = Field(
        default="localhost:50051",
        validation_alias=AliasChoices(ENDPOINT_VAR, "SPICEDB_ENDPOINT"),
        description="SpiceDB gRPC endpoint",
    )
    preshared_key: SecretStr = Field(
        min_length=1,
        validation_alias=AliasChoices(PRESHARED_KEY_VAR),
        description="SpiceDB preshared key (operator secret). No default; required at startup",
    )


def load_spicedb_settings() -> SpiceDBSettings:
    """Read the SpiceDB settings from the environment.

    Raises:
        ConfigurationError: The preshared key is unset or empty, or another value is invalid.
    """
    try:
        return SpiceDBSettings()
    except ValidationError as exc:
        raise ConfigurationError(
            f"SpiceDB settings are invalid. {PRESHARED_KEY_VAR} is required and has no "
            f"default. {exc}"
        ) from exc


__all__ = ["ENDPOINT_VAR", "PRESHARED_KEY_VAR", "SpiceDBSettings", "load_spicedb_settings"]
