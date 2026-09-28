"""Raster generation subpackage for asset_forge."""

from __future__ import annotations

from asset_forge.raster.battlemap_raster import generate_battlemap_png
from asset_forge.raster.png_codec import encode_png_rgba, parse_hex_color
from asset_forge.raster.token_raster import (
    generate_token_png,
    generate_token_portrait_png,
)
from asset_forge.raster.wardrobe_raster import (
    ATTIRE_PALETTES,
    ATTIRE_PROMPTS,
    generate_wardrobe_portrait_png,
)

__all__ = [
    "ATTIRE_PALETTES",
    "ATTIRE_PROMPTS",
    "encode_png_rgba",
    "generate_battlemap_png",
    "generate_token_png",
    "generate_token_portrait_png",
    "generate_wardrobe_portrait_png",
    "parse_hex_color",
]
