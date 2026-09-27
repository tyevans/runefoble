"""Point light and radiance mapper for Universal VTT (.dd2vtt / .uvtt) maps."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class BoardLightModel:
    """Point light source extracted from Universal VTT with radiance models."""

    light_id: str
    x: float
    y: float
    color_hex: str
    bright_radius: float
    dim_radius: float
    flicker_intensity: float = 0.0
    intensity: float = 1.0
    shadows: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["range"] = self.dim_radius
        d["position"] = {"x": self.x, "y": self.y}
        d["color"] = self.color_hex
        return d


def normalize_color_hex(raw_color: str | None) -> str:
    """Normalize UVTT color strings into standardized hex string."""
    if not raw_color:
        return "#ffffffff"
    c = raw_color.strip()
    if not c.startswith("#"):
        c = f"#{c}"
    return c.lower()


def parse_uvtt_light(light_data: dict[str, Any], index: int = 0) -> BoardLightModel:
    """Map UVTT light source into bright/dim radiance and flicker model."""
    pos = light_data.get("position", {})
    lx = float(pos.get("x", 0.0)) if isinstance(pos, dict) else 0.0
    ly = float(pos.get("y", 0.0)) if isinstance(pos, dict) else 0.0

    raw_range = float(light_data.get("range", 5.0))
    dim_radius = float(light_data.get("dim_radius", light_data.get("dim", raw_range)))
    bright_radius = float(
        light_data.get("bright_radius", light_data.get("bright", round(dim_radius * 0.5, 2)))
    )

    flicker = float(light_data.get("flicker_intensity", light_data.get("flicker", 0.0)))
    intensity = float(light_data.get("intensity", 1.0))
    shadows = bool(light_data.get("shadows", True))
    color_hex = normalize_color_hex(light_data.get("color") or light_data.get("color_hex"))
    light_id = str(light_data.get("id") or light_data.get("light_id") or f"light-{index + 1}")

    skip_keys = {
        "position",
        "range",
        "dim_radius",
        "dim",
        "bright_radius",
        "bright",
        "flicker_intensity",
        "flicker",
        "intensity",
        "shadows",
        "color",
        "color_hex",
        "id",
        "light_id",
    }
    return BoardLightModel(
        light_id=light_id,
        x=round(lx, 3),
        y=round(ly, 3),
        color_hex=color_hex,
        bright_radius=round(bright_radius, 2),
        dim_radius=round(dim_radius, 2),
        flicker_intensity=round(flicker, 2),
        intensity=round(intensity, 2),
        shadows=shadows,
        metadata={k: v for k, v in light_data.items() if k not in skip_keys},
    )


def extract_lights_from_uvtt(lights: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Parse list of UVTT lights into standardized board light dictionaries."""
    result: list[dict[str, Any]] = []
    for idx, l_data in enumerate(lights):
        if not isinstance(l_data, dict):
            continue
        model = parse_uvtt_light(l_data, index=idx)
        result.append(model.to_dict())
    return result
