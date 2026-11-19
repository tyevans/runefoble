"""Hazard damage table and the single walk over a movement path.

The walk yields the movement cost, the cells that are difficult, and the hazards a token
crosses. The move handler applies these results and the move preview reports them. Both
call `walk_path`, so they cannot disagree.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any

HAZARD_DAMAGE: dict[str, str] = {
    "lava": "2d10",
    "fire": "1d6",
    "acid": "2d6",
    "spikes": "2d4",
    "poison": "1d4",
}
DEFAULT_HAZARD_DICE = "1d6"


def is_known_hazard(hazard_type: str) -> bool:
    """Return True when the hazard type is in the hazard damage table. The match is exact."""
    return hazard_type in HAZARD_DAMAGE


def hazard_damage_dice(hazard_type: str | None) -> str:
    """Return the damage dice for a hazard type. Unlisted hazards use DEFAULT_HAZARD_DICE."""
    return HAZARD_DAMAGE.get((hazard_type or "").lower(), DEFAULT_HAZARD_DICE)


@dataclass(frozen=True)
class CellStep:
    """One cell that a token enters on a path."""

    x: int
    y: int
    is_difficult: bool
    hazard: str | None


@dataclass(frozen=True)
class PathWalk:
    """Result of walking a path over the board terrain."""

    steps: tuple[CellStep, ...]

    @property
    def cost(self) -> int:
        """Movement budget cost. Difficult terrain costs 2 per cell, other terrain costs 1."""
        return sum(2 if step.is_difficult else 1 for step in self.steps)

    @property
    def hazards(self) -> list[tuple[str, str]]:
        """Every (hazard_type, damage_dice) the path crosses, in path order."""
        return [(s.hazard, hazard_damage_dice(s.hazard)) for s in self.steps if s.hazard]

    @property
    def last_hazard(self) -> tuple[str, str] | None:
        """The last hazard on the path. A move reports this one as its hazard result."""
        hazards = self.hazards
        return hazards[-1] if hazards else None


def walk_path(
    path: Iterable[tuple[int, int]], get_terrain_fn: Callable[[int, int], Any]
) -> PathWalk:
    """Walk a path cell by cell and record difficulty and hazard for each cell."""
    steps: list[CellStep] = []
    for cx, cy in path:
        terrain = get_terrain_fn(cx, cy)
        is_difficult = getattr(terrain, "terrain_type", "normal") == "difficult"
        hazard = getattr(terrain, "hazard", None) if terrain else None
        steps.append(CellStep(cx, cy, is_difficult, hazard or None))
    return PathWalk(tuple(steps))
