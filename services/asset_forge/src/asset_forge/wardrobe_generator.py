"""Wardrobe image synthesis port and generator selection.

A wardrobe generator turns a character portrait and an attire prompt into PNG bytes.
The default generator is the deterministic placeholder. It draws a flat colour disk
for the face. It preserves no face. Other generators must implement the port and be
added to `build_wardrobe_generator`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from runefoble_platform.config import WardrobeGeneratorSettings
from runefoble_platform.engine_ports import build_adapter

from asset_forge.wardrobe_placeholder import PlaceholderWardrobeGenerator

PngBytes = bytes


@dataclass(frozen=True)
class WardrobePortrait:
    """Character and framing inputs for one wardrobe portrait."""

    character_name: str
    attire_type: str
    size_px: int
    border_color_hex: str


@runtime_checkable
class WardrobeGenerator(Protocol):
    """Port for wardrobe image synthesis."""

    name: str
    preserves_face: bool

    def generate(
        self,
        portrait: WardrobePortrait,
        attire_prompt: str,
        face_seed: str | None,
    ) -> PngBytes:
        """Return PNG bytes for the portrait in the requested attire."""
        ...


def build_wardrobe_generator(settings: WardrobeGeneratorSettings) -> WardrobeGenerator:
    """Return the generator named by settings. Unknown names fail at start-up."""
    return build_adapter(
        "RUNEFOBLE_WARDROBE_GENERATOR",
        settings.generator,
        {"placeholder": PlaceholderWardrobeGenerator},
    )
