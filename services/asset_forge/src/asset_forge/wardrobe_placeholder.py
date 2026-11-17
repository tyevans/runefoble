"""Placeholder wardrobe generator. It draws a flat colour portrait and preserves no face.

The face is a flat colour from a hash of the face seed or character name. The attire
is a flat palette fill with a sine fold. The attire prompt is not used to draw the
image. This generator is the default. It must not be described as a face-preserving
or prompt-driven generator.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from asset_forge.raster.wardrobe_raster import generate_wardrobe_portrait_png

if TYPE_CHECKING:
    from asset_forge.wardrobe_generator import WardrobePortrait


class PlaceholderWardrobeGenerator:
    """Deterministic placeholder. Ignores the attire prompt and preserves no face."""

    name: ClassVar[str] = "placeholder"
    preserves_face: ClassVar[bool] = False

    def generate(
        self,
        portrait: WardrobePortrait,
        attire_prompt: str,
        face_seed: str | None,
    ) -> bytes:
        """Draw the placeholder portrait for the given portrait inputs."""
        del attire_prompt  # The placeholder does not read the prompt.
        return generate_wardrobe_portrait_png(
            character_name=portrait.character_name,
            attire_type=portrait.attire_type,
            face_seed=face_seed,
            size_px=portrait.size_px,
            border_color_hex=portrait.border_color_hex,
        )
