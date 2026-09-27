"""Procedural 3D STL mesh generator for tabletop miniature bases and condition clips.

Generates mathematically watertight (2-manifold) binary and ASCII STL meshes
for 28mm and 50mm miniature bases featuring snap-in status condition clips.
"""

from __future__ import annotations

import math
import struct
from typing import Any

Triangle = tuple[
    tuple[float, float, float],
    tuple[float, float, float],
    tuple[float, float, float],
    tuple[float, float, float],
]


def _calc_normal(
    v1: tuple[float, float, float],
    v2: tuple[float, float, float],
    v3: tuple[float, float, float],
) -> tuple[float, float, float]:
    """Compute normalized surface normal for triangle using cross product."""
    ux, uy, uz = v2[0] - v1[0], v2[1] - v1[1], v2[2] - v1[2]
    vx, vy, vz = v3[0] - v1[0], v3[1] - v1[1], v3[2] - v1[2]
    nx = uy * vz - uz * vy
    ny = uz * vx - ux * vz
    nz = ux * vy - uy * vx
    mag = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
    return (nx / mag, ny / mag, nz / mag)


def _build_base_triangles(
    radius: float,
    height: float,
    segments: int,
    num_slots: int,
    slot_depth: float,
) -> list[Triangle]:
    """Generate watertight triangle list for miniature base disc with snap slots."""
    r_list: list[float] = []
    slot_interval = max(1, segments // max(1, num_slots))
    for i in range(segments):
        is_slot = (i % slot_interval) == 0 and num_slots > 0
        r_list.append(max(2.0, radius - slot_depth) if is_slot else radius)

    bot_pts: list[tuple[float, float, float]] = []
    top_pts: list[tuple[float, float, float]] = []
    for i in range(segments):
        th = 2.0 * math.pi * i / segments
        r = r_list[i]
        bot_pts.append((round(r * math.cos(th), 4), round(r * math.sin(th), 4), 0.0))
        top_pts.append((round(r * math.cos(th), 4), round(r * math.sin(th), 4), height))

    c_bot = (0.0, 0.0, 0.0)
    c_top = (0.0, 0.0, height)
    triangles: list[Triangle] = []

    for i in range(segments):
        j = (i + 1) % segments
        # Bottom cap (pointing down)
        b1, b2 = bot_pts[j], bot_pts[i]
        triangles.append((_calc_normal(c_bot, b1, b2), c_bot, b1, b2))
        # Top cap (pointing up)
        t1, t2 = top_pts[i], top_pts[j]
        triangles.append((_calc_normal(c_top, t1, t2), c_top, t1, t2))
        # Side wall quads (2 triangles per segment)
        bi, bj, ti, tj = bot_pts[i], bot_pts[j], top_pts[i], top_pts[j]
        triangles.append((_calc_normal(bi, bj, tj), bi, bj, tj))
        triangles.append((_calc_normal(bi, tj, ti), bi, tj, ti))

    return triangles


def generate_stl_mesh(
    diameter_mm: float = 28.0,
    height_mm: float = 3.5,
    num_slots: int = 4,
    slot_depth_mm: float = 1.5,
    condition_label: str = "Poisoned",
    binary: bool = True,
    segments: int = 36,
) -> tuple[bytes, dict[str, Any]]:
    """Generate watertight STL binary or ASCII mesh for 28mm/50mm miniature base."""
    radius = diameter_mm / 2.0
    triangles = _build_base_triangles(radius, height_mm, segments, num_slots, slot_depth_mm)
    facet_count = len(triangles)

    if binary:
        hdr = f"Runefoble Watertight STL {diameter_mm:.0f}mm Base [{condition_label}]".encode(
            "ascii"
        )
        header = hdr.ljust(80, b"\x00")[:80]
        body = bytearray(header + struct.pack("<I", facet_count))
        for norm, v1, v2, v3 in triangles:
            body.extend(
                struct.pack(
                    "<12fH",
                    norm[0],
                    norm[1],
                    norm[2],
                    v1[0],
                    v1[1],
                    v1[2],
                    v2[0],
                    v2[1],
                    v2[2],
                    v3[0],
                    v3[1],
                    v3[2],
                    0,
                )
            )
        data = bytes(body)
    else:
        lines = [f"solid runefoble_base_{diameter_mm:.0f}mm"]
        for norm, v1, v2, v3 in triangles:
            lines.append(f"  facet normal {norm[0]:.4f} {norm[1]:.4f} {norm[2]:.4f}")
            lines.append("    outer loop")
            lines.append(f"      vertex {v1[0]:.4f} {v1[1]:.4f} {v1[2]:.4f}")
            lines.append(f"      vertex {v2[0]:.4f} {v2[1]:.4f} {v2[2]:.4f}")
            lines.append(f"      vertex {v3[0]:.4f} {v3[1]:.4f} {v3[2]:.4f}")
            lines.append("    endloop")
            lines.append("  endfacet")
        lines.append("endsolid")
        data = "\n".join(lines).encode("utf-8")

    meta = {
        "diameter_mm": diameter_mm,
        "height_mm": height_mm,
        "facet_count": facet_count,
        "is_watertight": True,
        "num_slots": num_slots,
        "condition_label": condition_label,
        "byte_size": len(data),
    }
    return data, meta
