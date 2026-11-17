"""Map generators for the test composition root only.

Production code has no canned layout. Tests inject these generators through
set_map_generator to prove the port is used and to force the 503 path.
"""

from __future__ import annotations

from asset_forge.map_generator import MAP_GENERATION_UNAVAILABLE, MapGenerator, MapLayout
from asset_forge.models import WallSegment
from runefoble_platform.engine_ports import EngineUnavailableError

FIXTURE_THEME = "fixture_theme"


class FixtureMapGenerator(MapGenerator):
    """Returns one fixed wall and an open grid, whatever the prompt."""

    generator_name = "fixture"

    async def generate(
        self,
        prompt: str,
        width: int,
        height: int,
        seed: int | None,
        *,
        wall_density: float = 0.2,
        hazard_density: float = 0.1,
        theme_override: str | None = None,
    ) -> MapLayout:
        return MapLayout(
            theme=theme_override or FIXTURE_THEME,
            wall_segments=[WallSegment(x1=0, y1=0, x2=width, y2=0, wall_type="fixture")],
            hazard_cells=[],
            doors=[],
            grid=[[0] * width for _ in range(height)],
        )


class UnavailableMapGenerator(MapGenerator):
    """Always reports that it cannot produce a layout."""

    generator_name = "fixture"

    async def generate(
        self,
        prompt: str,
        width: int,
        height: int,
        seed: int | None,
        *,
        wall_density: float = 0.2,
        hazard_density: float = 0.1,
        theme_override: str | None = None,
    ) -> MapLayout:
        raise EngineUnavailableError(
            MAP_GENERATION_UNAVAILABLE,
            self.generator_name,
            "fixture generator is offline",
            engine_field="generator",
        )
