"""Procedural tactical battlemap raster generator with thematic palettes."""

from __future__ import annotations

from asset_forge.raster.png_codec import encode_png_rgba

THEME_PALETTES: dict[str, dict[str, tuple[int, int, int]]] = {
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

DEFAULT_PALETTE: dict[str, tuple[int, int, int]] = {
    "floor": (50, 52, 55),
    "wall": (22, 24, 26),
    "hazard": (40, 140, 50),  # Acidic sludge
    "grid": (70, 72, 75),
}


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

    palette = THEME_PALETTES.get(theme, DEFAULT_PALETTE)
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
