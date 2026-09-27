"""Procedural battlemap texture and circular token portrait raster synthesizer."""

from __future__ import annotations

import hashlib
import math
import struct
import zlib


def encode_png_rgba(width: int, height: int, rgba_bytes: bytes) -> bytes:
    """Encode raw RGBA byte buffer into a valid standard PNG image binary."""

    def make_chunk(tag: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(tag + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)

    header = b"\x89PNG\r\n\x1a\n"
    ihdr = make_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))

    scanlines = bytearray()
    row_bytes = width * 4
    for y in range(height):
        scanlines.append(0)  # Filter type: None
        start = y * row_bytes
        scanlines.extend(rgba_bytes[start : start + row_bytes])

    idat = make_chunk(b"IDAT", zlib.compress(bytes(scanlines), level=6))
    iend = make_chunk(b"IEND", b"")

    return header + ihdr + idat + iend


def parse_hex_color(hex_str: str) -> tuple[int, int, int]:
    """Parse hex string (#RRGGBB or RRGGBB) to (r, g, b) tuple."""
    clean = hex_str.lstrip("#")
    if len(clean) == 3:
        clean = "".join(c * 2 for c in clean)
    if len(clean) != 6:
        return (230, 57, 70)  # Default Bauhaus red
    try:
        r = int(clean[0:2], 16)
        g = int(clean[2:4], 16)
        b = int(clean[4:6], 16)
        return r, g, b
    except ValueError:
        return (230, 57, 70)


def generate_battlemap_png(
    grid: list[list[int]],
    theme: str,
    cell_size_px: int = 64,
) -> bytes:
    """Synthesize high-resolution tactical battlemap raster image with theme palette and grid lines."""
    height_cells = len(grid)
    width_cells = len(grid[0]) if height_cells > 0 else 0

    img_w = width_cells * cell_size_px
    img_h = height_cells * cell_size_px

    # Palettes per theme (floor, wall, hazard, grid_line)
    theme_palettes = {
        "dwarven_forge": {
            "floor": (42, 40, 48),
            "wall": (20, 18, 24),
            "hazard": (230, 80, 20),  # Molten lava
            "grid": (60, 55, 68),
        },
        "crypt": {
            "floor": (45, 48, 52),
            "wall": (18, 20, 24),
            "hazard": (90, 40, 120),  # Necrotic spikes / purple
            "grid": (65, 70, 78),
        },
        "swamp": {
            "floor": (35, 45, 30),
            "wall": (15, 25, 12),
            "hazard": (20, 60, 75),  # Murky deep water
            "grid": (55, 68, 48),
        },
        "arcane_sanctuary": {
            "floor": (30, 25, 55),
            "wall": (15, 10, 30),
            "hazard": (180, 30, 160),  # Arcane void / magenta
            "grid": (50, 45, 80),
        },
    }
    palette = theme_palettes.get(
        theme,
        {
            "floor": (50, 52, 55),
            "wall": (22, 24, 26),
            "hazard": (40, 140, 50),  # Acidic sludge
            "grid": (70, 72, 75),
        },
    )

    buffer = bytearray(img_w * img_h * 4)

    for y in range(img_h):
        cell_y = y // cell_size_px
        is_grid_y = (y % cell_size_px) == 0 or (y % cell_size_px) == (cell_size_px - 1)
        row_offset = y * img_w * 4

        for x in range(img_w):
            cell_x = x // cell_size_px
            is_grid_x = (x % cell_size_px) == 0 or (x % cell_size_px) == (cell_size_px - 1)

            cell_type = grid[cell_y][cell_x]
            if is_grid_x or is_grid_y:
                r, g, b = palette["grid"]
            elif cell_type == 1:
                r, g, b = palette["wall"]
            elif cell_type == 2:
                # Add slight flame / fluid noise to hazard
                noise = ((x * 13 + y * 7) % 25) - 12
                base_r, base_g, base_b = palette["hazard"]
                r = max(0, min(255, base_r + noise))
                g = max(0, min(255, base_g + noise // 2))
                b = max(0, min(255, base_b + noise // 3))
            else:
                # Subtle tile texture variation
                tile_noise = ((x * 17 + y * 31) % 15) - 7
                base_r, base_g, base_b = palette["floor"]
                r = max(0, min(255, base_r + tile_noise))
                g = max(0, min(255, base_g + tile_noise))
                b = max(0, min(255, base_b + tile_noise))

            pixel_idx = row_offset + (x * 4)
            buffer[pixel_idx] = r
            buffer[pixel_idx + 1] = g
            buffer[pixel_idx + 2] = b
            buffer[pixel_idx + 3] = 255  # Fully opaque

    return encode_png_rgba(img_w, img_h, bytes(buffer))


def generate_token_portrait_png(
    token_name: str,
    prompt: str,
    token_type: str = "pc",
    size_px: int = 256,
    crop_style: str = "circular",
    border_color_hex: str = "#e63946",
    border_width: int = 8,
    transparent_background: bool = True,
) -> bytes:
    """Synthesize stylistic cropped circular token portrait with alpha transparency."""
    border_r, border_g, border_b = parse_hex_color(border_color_hex)
    seed = int(hashlib.sha256(f"{token_name}:{prompt}:{token_type}".encode()).hexdigest()[:8], 16)

    # Class / entity color tint from seed
    tint_r = 50 + (seed % 150)
    tint_g = 50 + ((seed >> 8) % 150)
    tint_b = 50 + ((seed >> 16) % 150)

    center = size_px / 2.0
    radius = center - 1.0
    inner_radius = radius - border_width

    buffer = bytearray(size_px * size_px * 4)

    for y in range(size_px):
        dy = y - center + 0.5
        row_offset = y * size_px * 4

        for x in range(size_px):
            dx = x - center + 0.5
            dist = math.sqrt(dx * dx + dy * dy)
            pixel_idx = row_offset + (x * 4)

            if crop_style == "circular":
                if dist > radius:
                    if transparent_background:
                        buffer[pixel_idx : pixel_idx + 4] = b"\x00\x00\x00\x00"
                        continue
                    else:
                        buffer[pixel_idx : pixel_idx + 4] = b"\x12\x12\x12\xff"
                        continue
                elif dist >= inner_radius:
                    # Border ring
                    buffer[pixel_idx] = border_r
                    buffer[pixel_idx + 1] = border_g
                    buffer[pixel_idx + 2] = border_b
                    buffer[pixel_idx + 3] = 255
                    continue

            # Interior Portrait Canvas
            # Create a stylized radial gradient with character silhouette
            norm_dist = dist / max(inner_radius, 1.0)
            grad = 1.0 - (norm_dist * 0.4)

            # Procedural silhouette patterning
            angle = math.atan2(dy, dx)
            pattern = math.sin(angle * 4 + norm_dist * 5) * 0.15

            # Base colors
            pr = int(min(255, max(0, tint_r * grad * (1.0 + pattern))))
            pg = int(min(255, max(0, tint_g * grad * (1.0 + pattern))))
            pb = int(min(255, max(0, tint_b * grad * (1.0 + pattern))))

            # Eye or crest emblem in center
            if norm_dist < 0.25:
                pr = min(255, pr + 60)
                pg = min(255, pg + 60)
                pb = min(255, pb + 60)

            buffer[pixel_idx] = pr
            buffer[pixel_idx + 1] = pg
            buffer[pixel_idx + 2] = pb
            buffer[pixel_idx + 3] = 255

    return encode_png_rgba(size_px, size_px, bytes(buffer))


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
        attire_type,
        f"Thematic {attire_type} outfit preserving character facial identity.",
    )
    final_prompt = f"{template_prompt} {custom_prompt or ''}".strip()
    attire_rgb = ATTIRE_PALETTES.get(attire_type, (200, 150, 50))
    border_r, border_g, border_b = parse_hex_color(border_color_hex)

    # Face embedding seed preserves character facial identity across all wardrobe variants
    f_seed = face_seed or character_name
    seed_int = int(hashlib.sha256(f_seed.encode()).hexdigest()[:8], 16)
    face_r = 60 + (seed_int % 140)
    face_g = 60 + ((seed_int >> 8) % 140)
    face_b = 60 + ((seed_int >> 16) % 140)

    center = size_px / 2.0
    radius = center - 1.0
    inner_radius = radius - 8

    buffer = bytearray(size_px * size_px * 4)

    for y in range(size_px):
        dy = y - center + 0.5
        row_offset = y * size_px * 4

        for x in range(size_px):
            dx = x - center + 0.5
            dist = math.sqrt(dx * dx + dy * dy)
            pixel_idx = row_offset + (x * 4)

            if dist > radius:
                # Transparent outside circle
                buffer[pixel_idx : pixel_idx + 4] = b"\x00\x00\x00\x00"
                continue
            elif dist >= inner_radius:
                # Outer border ring
                buffer[pixel_idx] = border_r
                buffer[pixel_idx + 1] = border_g
                buffer[pixel_idx + 2] = border_b
                buffer[pixel_idx + 3] = 255
                continue

            # Interior canvas: Upper half is face/head, lower half is attire/clothing
            norm_y = y / size_px
            norm_dist = dist / max(inner_radius, 1.0)
            angle = math.atan2(dy, dx)

            if norm_y < 0.45:
                # Facial region preserving base character identity
                grad = 1.0 - (norm_dist * 0.3)
                pr = int(min(255, max(0, face_r * grad)))
                pg = int(min(255, max(0, face_g * grad)))
                pb = int(min(255, max(0, face_b * grad)))
                # Eye glint
                if 0.28 < norm_y < 0.35 and abs(dx) < 25:
                    pr = min(255, pr + 50)
                    pg = min(255, pg + 50)
                    pb = min(255, pb + 50)
            else:
                # Attire region with thematic attire palette & folds
                fold = math.sin(angle * 6 + norm_y * 10) * 0.2
                pr = int(min(255, max(0, attire_rgb[0] * (0.8 + fold))))
                pg = int(min(255, max(0, attire_rgb[1] * (0.8 + fold))))
                pb = int(min(255, max(0, attire_rgb[2] * (0.8 + fold))))

            buffer[pixel_idx] = pr
            buffer[pixel_idx + 1] = pg
            buffer[pixel_idx + 2] = pb
            buffer[pixel_idx + 3] = 255

    png_bytes = encode_png_rgba(size_px, size_px, bytes(buffer))
    return png_bytes, final_prompt
