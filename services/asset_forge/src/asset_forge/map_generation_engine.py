"""Process-wide battlemap generator selected from configuration."""

from __future__ import annotations

from asset_forge.map_generator import MapGenerator
from asset_forge.map_generator_settings import AssetForgeSettings, build_map_generator

_map_generator: MapGenerator | None = None


def get_map_generator() -> MapGenerator:
    global _map_generator
    if _map_generator is None:
        _map_generator = build_map_generator(AssetForgeSettings())
    return _map_generator


def set_map_generator(generator: MapGenerator | None) -> None:
    """Replace the generator. Pass None to rebuild it from settings on next use."""
    global _map_generator
    _map_generator = generator
