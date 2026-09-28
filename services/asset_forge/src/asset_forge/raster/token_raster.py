"""Circular token portrait generator with borders and alpha transparency."""

from __future__ import annotations

import hashlib
import math

from asset_forge.raster.png_codec import encode_png_rgba, parse_hex_color


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
                    buffer[pixel_idx : pixel_idx + 4] = b"\x12\x12\x12\xff"
                    continue
                if dist >= inner_radius:
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


# Backward compatibility alias
generate_token_png = generate_token_portrait_png
