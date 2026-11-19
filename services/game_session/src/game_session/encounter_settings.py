"""Settings for the encounter board that game_session requests from board_state (TASK-0749).

The grid size of a new encounter board is owned here, not by the MCP gateway (ADR-0015 b).
"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class EncounterGridSettings(BaseSettings):
    """Grid size for an encounter board that board_state creates when the session has none."""

    model_config = SettingsConfigDict(env_prefix="RUNEFOBLE_ENCOUNTER_", extra="ignore")

    cols: int = Field(default=10, ge=1)
    rows: int = Field(default=8, ge=1)
