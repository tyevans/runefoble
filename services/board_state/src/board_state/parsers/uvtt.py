"""Universal VTT (.dd2vtt) map format parser and Silo S3 asset pipeline.

Parses Dungeondraft and Universal VTT JSON files:
- Grid resolution and canvas dimensions
- Line-of-sight wall vectors and collision boundaries
- Portals and door coordinate intervals
- Ambient light sources and radii
- Embedded base64 background map texture extraction and Silo S3 persistence
"""

from __future__ import annotations

import base64
import json
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from board_state.uvtt.doors import extract_doors_from_uvtt
from board_state.uvtt.lights import extract_lights_from_uvtt
from runefoble_platform.storage import SiloStorageService, get_storage_service

if TYPE_CHECKING:
    from board_state.aggregate import BoardAggregate
    from board_state.models import BoardState

logger = logging.getLogger("runefoble.board_state.parsers.uvtt")


@dataclass
class UVTTParseResult:
    """Structured extraction result from a Universal VTT (.dd2vtt) file."""

    cols: int
    rows: int
    pixels_per_grid: int
    wall_segments: list[dict[str, Any]] = field(default_factory=list)
    portals: list[dict[str, Any]] = field(default_factory=list)
    doors: dict[str, Any] = field(default_factory=dict)
    lights: list[dict[str, Any]] = field(default_factory=list)
    image_bytes: bytes | None = None
    image_mime_type: str = "image/png"


def detect_image_mime_type(data: bytes) -> str:
    """Detect image MIME type from magic byte headers."""
    if data.startswith(b"\x89PNG"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return "image/png"


def parse_uvtt_data(raw_data: str | bytes | dict[str, Any]) -> UVTTParseResult:
    """Parse Universal VTT (.dd2vtt) payload into structured geometry and textures."""
    if isinstance(raw_data, bytes):
        payload = json.loads(raw_data.decode("utf-8"))
    elif isinstance(raw_data, str):
        payload = json.loads(raw_data)
    elif isinstance(raw_data, dict):
        payload = raw_data
    else:
        raise ValueError(f"Unsupported UVTT payload type: {type(raw_data).__name__}")

    # 1. Grid resolution and dimensions
    resolution = payload.get("resolution", {})
    map_size = resolution.get("map_size", {})
    if isinstance(map_size, dict):
        cols = int(round(float(map_size.get("x", 20))))
        rows = int(round(float(map_size.get("y", 20))))
    elif isinstance(map_size, (list, tuple)) and len(map_size) >= 2:
        cols = int(round(float(map_size[0])))
        rows = int(round(float(map_size[1])))
    else:
        cols = int(round(float(payload.get("cols", payload.get("width", 20)))))
        rows = int(round(float(payload.get("rows", payload.get("height", 20)))))

    cols = max(1, cols)
    rows = max(1, rows)
    pixels_per_grid = int(round(float(resolution.get("pixels_per_grid", 70))))

    # 2. Line of sight (walls)
    wall_segments: list[dict[str, Any]] = []
    los_chains = payload.get("line_of_sight", [])
    for chain in los_chains:
        if not isinstance(chain, list) or len(chain) < 2:
            continue
        for i in range(len(chain) - 1):
            p1 = chain[i]
            p2 = chain[i + 1]
            if isinstance(p1, dict) and isinstance(p2, dict):
                x1 = float(p1.get("x", 0.0))
                y1 = float(p1.get("y", 0.0))
                x2 = float(p2.get("x", 0.0))
                y2 = float(p2.get("y", 0.0))
                wall_segments.append(
                    {
                        "x1": round(x1, 3),
                        "y1": round(y1, 3),
                        "x2": round(x2, 3),
                        "y2": round(y2, 3),
                        "wall_type": "wall",
                    }
                )

    # 3. Portals & Doors
    raw_portals = payload.get("portals", [])
    doors = extract_doors_from_uvtt(raw_portals)
    portals: list[dict[str, Any]] = []
    for portal in raw_portals:
        if not isinstance(portal, dict):
            continue
        pos = portal.get("position", {})
        px = float(pos.get("x", 0.0)) if isinstance(pos, dict) else 0.0
        py = float(pos.get("y", 0.0)) if isinstance(pos, dict) else 0.0
        portals.append(
            {
                "position": {"x": round(px, 3), "y": round(py, 3)},
                "bounds": portal.get("bounds", []),
                "rotation": float(portal.get("rotation", 0.0)),
                "closed": bool(portal.get("closed", True)),
                "freestanding": bool(portal.get("freestanding", False)),
            }
        )

    # 4. Ambient & Point Lights
    raw_lights = payload.get("lights", [])
    lights = extract_lights_from_uvtt(raw_lights)
    if not lights:
        # Fallback empty list if none extracted
        lights = []

    # 5. Base64 Map Texture
    image_bytes = None
    image_mime_type = "image/png"
    raw_img = payload.get("image")
    if raw_img and isinstance(raw_img, str):
        try:
            # Handle data URL prefix if present
            if "base64," in raw_img:
                raw_img = raw_img.split("base64,", 1)[1]
            image_bytes = base64.b64decode(raw_img)
            image_mime_type = detect_image_mime_type(image_bytes)
        except Exception as exc:
            logger.warning("Failed to decode embedded UVTT base64 image: %s", exc)

    return UVTTParseResult(
        cols=cols,
        rows=rows,
        pixels_per_grid=pixels_per_grid,
        wall_segments=wall_segments,
        portals=portals,
        doors=doors,
        lights=lights,
        image_bytes=image_bytes,
        image_mime_type=image_mime_type,
    )


def store_uvtt_image(
    image_bytes: bytes,
    mime_type: str = "image/png",
    storage: SiloStorageService | None = None,
    owner_id: str = "uvtt_importer",
) -> tuple[str, str]:
    """Store decoded battlemap image into Silo S3 and return (asset_id, url)."""
    s = storage or get_storage_service()
    asset_id = f"map-{uuid4().hex[:12]}"
    ext = "jpg" if "jpeg" in mime_type else ("webp" if "webp" in mime_type else "png")
    object_key = f"battlemaps/{asset_id}.{ext}"

    metadata = s.upload_asset(
        bucket=s.default_bucket,
        object_key=object_key,
        data=image_bytes,
        content_type=mime_type,
        owner_id=owner_id,
        asset_id=asset_id,
    )
    return asset_id, metadata["url"]


def apply_uvtt_to_board(
    board: BoardAggregate,
    parsed: UVTTParseResult,
    asset_id: str | None = None,
    image_url: str | None = None,
) -> BoardState:
    """Mutate BoardAggregate state with parsed Universal VTT layout, geometry, and image."""
    board.import_uvtt_map(
        cols=parsed.cols,
        rows=parsed.rows,
        pixels_per_grid=parsed.pixels_per_grid,
        background_asset_id=asset_id,
        background_image_url=image_url,
        wall_segments=parsed.wall_segments,
        portals=parsed.portals,
        doors=parsed.doors,
        lights=parsed.lights,
    )
    return board.state
