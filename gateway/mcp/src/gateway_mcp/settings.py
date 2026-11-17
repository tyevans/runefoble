"""Upstream service addresses for the MCP gateway adapters."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class GatewayMcpSettings(BaseSettings):
    """Base URLs of the owning services that MCP tools call over HTTP."""

    model_config = SettingsConfigDict(extra="ignore")

    board_state_url: str = Field(
        default="http://localhost:8002",
        description="Base URL of the board_state service (BOARD_STATE_URL).",
    )
    character_sheet_url: str = Field(
        default="http://localhost:8003",
        description="Base URL of the character_sheet service (CHARACTER_SHEET_URL).",
    )
    game_session_url: str = Field(
        default="http://localhost:8004",
        description="Base URL of the game_session service (GAME_SESSION_URL).",
    )
    rules_compendium_url: str = Field(
        default="http://localhost:8007",
        description="Base URL of the rules_compendium service (RULES_COMPENDIUM_URL).",
    )
    the_watcher_url: str = Field(
        default="http://localhost:8001",
        description="Base URL of the the_watcher service (THE_WATCHER_URL).",
    )


def load_settings() -> GatewayMcpSettings:
    """Read gateway upstream settings from the environment on each call."""
    return GatewayMcpSettings()
