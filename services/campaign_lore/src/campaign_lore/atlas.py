"""Interactive Multi-Layered World Atlas Engine.

Provides deep-zoom coordinate projections across continental, regional, and municipal layers,
polygon territory containment checks, contested boundary highlights, and chronological era filtering.
"""

from typing import Any

LAYER_SCALES: dict[str, float] = {
    "continental": 1.0,
    "regional": 4.0,
    "municipal": 16.0,
}

BASE_WORLD_EXTENT = 1000.0


class CoordinateProjection:
    """Coordinate projection system supporting deep-zoom layers."""

    @classmethod
    def get_layer_extent(cls, layer: str) -> float:
        """Return the coordinate extent for a given map layer."""
        scale = LAYER_SCALES.get(layer.lower(), 1.0)
        return BASE_WORLD_EXTENT * scale

    @classmethod
    def normalize(cls, x: float, y: float, layer: str = "continental") -> tuple[float, float]:
        """Convert layer coordinates into normalized [0.0, 1.0] spatial bounds."""
        extent = cls.get_layer_extent(layer)
        norm_x = max(0.0, min(1.0, x / extent))
        norm_y = max(0.0, min(1.0, y / extent))
        return (norm_x, norm_y)

    @classmethod
    def denormalize(
        cls, norm_x: float, norm_y: float, layer: str = "continental"
    ) -> tuple[float, float]:
        """Convert normalized [0.0, 1.0] coordinates to layer coordinates."""
        extent = cls.get_layer_extent(layer)
        px = max(0.0, min(1.0, norm_x)) * extent
        py = max(0.0, min(1.0, norm_y)) * extent
        return (px, py)

    @classmethod
    def project_coordinates(
        cls,
        x: float,
        y: float,
        source_layer: str,
        target_layer: str,
    ) -> dict[str, float]:
        """Project spatial coordinates directly from source layer to target layer."""
        norm_x, norm_y = cls.normalize(x, y, source_layer)
        proj_x, proj_y = cls.denormalize(norm_x, norm_y, target_layer)
        return {
            "x": round(proj_x, 2),
            "y": round(proj_y, 2),
            "normalized_x": round(norm_x, 4),
            "normalized_y": round(norm_y, 4),
            "target_layer": target_layer,
        }


def point_in_polygon(
    point: tuple[float, float] | dict[str, float],
    polygon: list[list[float]] | list[tuple[float, float]],
) -> bool:
    """Determine whether a 2D point lies within an arbitrary polygon using ray casting."""
    if len(polygon) < 3:
        return False

    if isinstance(point, dict):
        px, py = point.get("x", 0.0), point.get("y", 0.0)
    else:
        px, py = point[0], point[1]

    inside = False
    n = len(polygon)
    p1x, p1y = polygon[0][0], polygon[0][1]

    for i in range(1, n + 1):
        p2x, p2y = polygon[i % n][0], polygon[i % n][1]
        if py > min(p1y, p2y) and py <= max(p1y, p2y) and px <= max(p1x, p2x):
            if p1y != p2y:
                xints = (py - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
            if p1x == p2x or px <= xints:
                inside = not inside
        p1x, p1y = p2x, p2y

    return inside


def find_containing_territory(
    point: tuple[float, float] | dict[str, float],
    territories: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Identify the territory containing the specified point."""
    for territory in territories:
        coords = territory.get("polygon_coordinates") or []
        if coords and point_in_polygon(point, coords):
            return territory
    return None


def detect_contested_zones(
    territories: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Extract highlighted contested boundary zones and claiming factions."""
    contested_zones: list[dict[str, Any]] = []
    for terr in territories:
        if terr.get("is_contested"):
            contested_zones.append(
                {
                    "territory_id": str(terr.get("territory_id", "")),
                    "name": terr.get("name", "Contested Realm"),
                    "owner_faction": terr.get("owner_faction", "Disputed"),
                    "polygon_coordinates": terr.get("polygon_coordinates", []),
                    "contested_alert": f"Boundary dispute in {terr.get('name', 'Territory')}",
                    "highlight_color": "#e63946",
                    "border_style": "dashed",
                }
            )
    return contested_zones


def filter_features_by_era(
    features: list[dict[str, Any]],
    target_era: str | None = None,
    session_id: str | None = None,
) -> list[dict[str, Any]]:
    """Filter milestone pins or geopolitical boundaries by chronological era or session."""
    if not target_era and not session_id:
        return features

    filtered: list[dict[str, Any]] = []
    for item in features:
        item_era = item.get("era")
        item_sess = item.get("session_id")

        if target_era and item_era and target_era.strip().lower() in str(item_era).strip().lower():
            filtered.append(item)
            continue

        if session_id and item_sess and str(session_id).strip() == str(item_sess).strip():
            filtered.append(item)
            continue

        # If item has no era specified, include if neither filter strictly excluded it
        if not target_era and not session_id:
            filtered.append(item)

    return filtered
