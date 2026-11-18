"""Upstream service addresses and listen address for the MCP gateway."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class GatewayMcpSettings(BaseSettings):
    """Base URLs of the owning services that MCP tools call over HTTP.

    Every URL is required. The gateway has no localhost defaults, so a deployment that
    omits one fails at start-up and names the missing variable.
    """

    model_config = SettingsConfigDict(extra="ignore")

    board_state_url: str = Field(
        validation_alias="BOARD_STATE_URL",
        description="Base URL of the board_state service (BOARD_STATE_URL).",
    )
    character_sheet_url: str = Field(
        validation_alias="CHARACTER_SHEET_URL",
        description="Base URL of the character_sheet service (CHARACTER_SHEET_URL).",
    )
    game_session_url: str = Field(
        validation_alias="GAME_SESSION_URL",
        description="Base URL of the game_session service (GAME_SESSION_URL).",
    )
    rules_compendium_url: str = Field(
        validation_alias="RULES_COMPENDIUM_URL",
        description="Base URL of the rules_compendium service (RULES_COMPENDIUM_URL).",
    )
    the_watcher_url: str = Field(
        validation_alias="THE_WATCHER_URL",
        description="Base URL of the the_watcher service (THE_WATCHER_URL).",
    )


class GatewayMcpListenSettings(BaseSettings):
    """Address on which the streamable HTTP MCP endpoint listens (GATEWAY_MCP_HOST/PORT)."""

    model_config = SettingsConfigDict(env_prefix="GATEWAY_MCP_", extra="ignore")

    host: str = Field(default="0.0.0.0", description="Bind address (GATEWAY_MCP_HOST).")
    port: int = Field(default=8012, description="Bind port (GATEWAY_MCP_PORT).")


def load_settings() -> GatewayMcpSettings:
    """Read gateway upstream settings from the environment on each call."""
    return GatewayMcpSettings()


def load_listen_settings() -> GatewayMcpListenSettings:
    """Read the listen address from the environment on each call."""
    return GatewayMcpListenSettings()
