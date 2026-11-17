"""Battlemap layout port: the MapGenerator contract and the layout it returns."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import ClassVar

from asset_forge.models import DoorSegment, HazardCell, WallSegment

MAP_GENERATION_UNAVAILABLE = "map_generation_unavailable"


@dataclass(frozen=True)
class MapLayout:
    """Tactical grid layout: 0 = open floor, 1 = wall obstacle, 2 = hazard."""

    theme: str
    wall_segments: list[WallSegment]
    hazard_cells: list[HazardCell]
    doors: list[DoorSegment]
    grid: list[list[int]]


class MapGenerator(ABC):
    """Port: produces a battlemap layout from a prompt, a size and a seed.

    The seed selects one layout for a given prompt and size. A seed of None
    lets the generator derive a stable seed from the prompt and the size.
    """

    generator_name: ClassVar[str]

    @abstractmethod
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
        """Return the layout for the request.

        Raises EngineUnavailableError(MAP_GENERATION_UNAVAILABLE, engine, message,
        engine_field="generator") when no layout is produced.
        """
