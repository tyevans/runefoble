"""Standard PNG chunk encoding and hex color parsing primitives."""

from __future__ import annotations

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
