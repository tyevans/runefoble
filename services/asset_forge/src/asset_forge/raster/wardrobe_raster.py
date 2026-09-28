"""Procedural wardrobe portrait and attire variant synthesizer."""

from __future__ import annotations

import hashlib
import math

from asset_forge.raster.png_codec import encode_png_rgba, parse_hex_color

ATTIRE_PROMPTS: dict[str, str] = {
    "ballroom_masquerade": (
        "Ornate royal masquerade ball attire, gilded filigree Venetian mask, "
        "embroidered velvet mantle, crystal chandelier reflections, preserving character facial identity."
    ),
    "arctic_tundra": (
        "Heavy frost-warden wolf pelt mantle, rime-encrusted leather armor, "
        "frosted breath in arctic blizzard, preserving character facial identity."
    ),
    "tavern_casual": (
        "Relaxed tavern casual traveler attire, unbuttoned linen tunic, leather belt and tankard, "
        "warm amber candlelight, preserving character facial identity."
    ),
    "battle_damaged": (
        "Scorched battlefield plate harness, soot smudges, battered iron pauldrons, "
        "glowing embers in smoky atmosphere, preserving character facial identity."
    ),
    "ceremonial": (
        "Sacred high ceremonial silk vestments, glowing celestial rune trim, "
        "coronation circlet, ethereal temple radiance, preserving character facial identity."
    ),
}

ATTIRE_PALETTES: dict[str, tuple[int, int, int]] = {
    "ballroom_masquerade": (212, 175, 55),
    "arctic_tundra": (168, 218, 220),
    "tavern_casual": (218, 165, 32),
    "battle_damaged": (180, 50, 50),
    "ceremonial": (186, 85, 211),
}


def generate_wardrobe_portrait_png(
    character_name: str,
    attire_type: str = "ballroom_masquerade",
    custom_prompt: str | None = None,
    face_seed: str | None = None,
    size_px: int = 256,
    border_color_hex: str = "#e63946",
) -> tuple[bytes, str]:
    """Synthesize wardrobe attire portrait variant preserving character facial features and palette."""
    template_prompt = ATTIRE_PROMPTS.get(
        attire_type, f"Thematic {attire_type} outfit preserving character facial identity."
    )
    final_prompt = f"{template_prompt} {custom_prompt or ''}".strip()
    attire_rgb = ATTIRE_PALETTES.get(attire_type, (200, 150, 50))
    border_r, border_g, border_b = parse_hex_color(border_color_hex)

    f_seed = face_seed or character_name
    seed_int = int(hashlib.sha256(f_seed.encode()).hexdigest()[:8], 16)
    face_r, face_g, face_b = (
        60 + (seed_int % 140),
        60 + ((seed_int >> 8) % 140),
        60 + ((seed_int >> 16) % 140),
    )

    center = size_px / 2.0
    radius = center - 1.0
    inner_radius = radius - 8
    buffer = bytearray(size_px * size_px * 4)

    for y in range(size_px):
        dy = y - center + 0.5
        row_offset = y * size_px * 4
        norm_y = y / size_px

        for x in range(size_px):
            dx = x - center + 0.5
            dist = math.sqrt(dx * dx + dy * dy)
            pixel_idx = row_offset + (x * 4)

            if dist > radius:
                buffer[pixel_idx : pixel_idx + 4] = b"\x00\x00\x00\x00"
                continue
            if dist >= inner_radius:
                buffer[pixel_idx : pixel_idx + 4] = bytes((border_r, border_g, border_b, 255))
                continue

            norm_dist = dist / max(inner_radius, 1.0)
            angle = math.atan2(dy, dx)
            if norm_y < 0.45:
                grad = 1.0 - (norm_dist * 0.3)
                pr, pg, pb = (
                    int(min(255, max(0, face_r * grad))),
                    int(min(255, max(0, face_g * grad))),
                    int(min(255, max(0, face_b * grad))),
                )
                if 0.28 < norm_y < 0.35 and abs(dx) < 25:
                    pr, pg, pb = min(255, pr + 50), min(255, pg + 50), min(255, pb + 50)
            else:
                fold = math.sin(angle * 6 + norm_y * 10) * 0.2
                pr = int(min(255, max(0, attire_rgb[0] * (0.8 + fold))))
                pg = int(min(255, max(0, attire_rgb[1] * (0.8 + fold))))
                pb = int(min(255, max(0, attire_rgb[2] * (0.8 + fold))))

            buffer[pixel_idx : pixel_idx + 4] = bytes((pr, pg, pb, 255))

    return encode_png_rgba(size_px, size_px, bytes(buffer)), final_prompt
