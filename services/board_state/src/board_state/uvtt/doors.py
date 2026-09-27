"""Door and portal geometry extractor for Universal VTT (.dd2vtt / .uvtt) maps."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class DoorGeometry:
    """Parsed interactive door or portal from Universal VTT geometry."""

    door_id: str
    x1: float
    y1: float
    x2: float
    y2: float
    pivot_x: float
    pivot_y: float
    status: str = "closed"
    is_open: bool = False
    is_locked: bool = False
    is_secret: bool = False
    detection_dc: int = 15
    rotation: float = 0.0
    freestanding: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def parse_uvtt_door(portal_data: dict[str, Any], index: int = 0) -> DoorGeometry:
    """Extract door coordinates, pivot hinge, status, and secret detection DC."""
    pos = portal_data.get("position", {})
    px = float(pos.get("x", 0.0)) if isinstance(pos, dict) else 0.0
    py = float(pos.get("y", 0.0)) if isinstance(pos, dict) else 0.0

    bounds = portal_data.get("bounds", [])
    if isinstance(bounds, list) and len(bounds) >= 2:
        b0, b1 = bounds[0], bounds[1]
        x1 = float(b0.get("x", px - 0.5)) if isinstance(b0, dict) else px - 0.5
        y1 = float(b0.get("y", py)) if isinstance(b0, dict) else py
        x2 = float(b1.get("x", px + 0.5)) if isinstance(b1, dict) else px + 0.5
        y2 = float(b1.get("y", py)) if isinstance(b1, dict) else py
    else:
        x1, y1 = px - 0.5, py
        x2, y2 = px + 0.5, py

    pivot = portal_data.get("pivot") or portal_data.get("hinge")
    if isinstance(pivot, dict) and "x" in pivot and "y" in pivot:
        pivot_x = float(pivot["x"])
        pivot_y = float(pivot["y"])
    else:
        pivot_x, pivot_y = x1, y1

    is_locked = bool(portal_data.get("locked", False))
    raw_closed = portal_data.get("closed")
    is_closed = (
        bool(raw_closed) if raw_closed is not None else not bool(portal_data.get("open", False))
    )

    if is_locked:
        status, is_open = "locked", False
    elif not is_closed or portal_data.get("status") == "open":
        status, is_open = "open", True
    else:
        status, is_open = "closed", False

    is_secret = bool(portal_data.get("secret", portal_data.get("is_secret", False)))
    dc_val = (
        portal_data.get("detection_dc")
        or portal_data.get("secret_dc")
        or portal_data.get("dc_detection")
    )
    detection_dc = int(dc_val) if dc_val is not None else (15 if is_secret else 10)
    door_id = str(portal_data.get("id") or portal_data.get("door_id") or f"door-{index + 1}")

    skip_keys = {
        "bounds",
        "pivot",
        "hinge",
        "closed",
        "open",
        "locked",
        "secret",
        "is_secret",
        "detection_dc",
        "secret_dc",
        "dc_detection",
        "rotation",
        "freestanding",
        "id",
        "door_id",
    }
    return DoorGeometry(
        door_id=door_id,
        x1=round(x1, 3),
        y1=round(y1, 3),
        x2=round(x2, 3),
        y2=round(y2, 3),
        pivot_x=round(pivot_x, 3),
        pivot_y=round(pivot_y, 3),
        status=status,
        is_open=is_open,
        is_locked=is_locked,
        is_secret=is_secret,
        detection_dc=detection_dc,
        rotation=float(portal_data.get("rotation", 0.0)),
        freestanding=bool(portal_data.get("freestanding", False)),
        metadata={k: v for k, v in portal_data.items() if k not in skip_keys},
    )


def extract_doors_from_uvtt(portals: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Parse list of UVTT portal dictionaries into door geometry mapping."""
    doors: dict[str, dict[str, Any]] = {}
    for idx, p in enumerate(portals):
        if not isinstance(p, dict):
            continue
        door = parse_uvtt_door(p, index=idx)
        doors[door.door_id] = door.to_dict()
    return doors
