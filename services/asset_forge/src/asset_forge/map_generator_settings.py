"""Asset Forge settings and the battlemap generator selection step."""

from __future__ import annotations

from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict
from runefoble_platform.engine_ports import build_adapter

from asset_forge.deterministic_map_generator import DeterministicMapGenerator
from asset_forge.map_generator import MapGenerator


class AssetForgeSettings(BaseSettings):
    """Environment configuration for Asset Forge (prefix RUNEFOBLE_ASSET_FORGE_).

    `map_generator` selects the battlemap layout adapter. `deterministic` is the
    built-in default. A configured external provider must implement MapGenerator.
    """

    model_config = SettingsConfigDict(
        env_prefix="RUNEFOBLE_ASSET_FORGE_",
        env_file=".env",
        extra="ignore",
    )

    map_generator: Literal["deterministic"] = "deterministic"


def build_map_generator(settings: AssetForgeSettings) -> MapGenerator:
    """Select the configured battlemap layout adapter."""
    return build_adapter(
        "RUNEFOBLE_ASSET_FORGE_MAP_GENERATOR",
        settings.map_generator,
        {"deterministic": DeterministicMapGenerator},
    )
