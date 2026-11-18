"""Tier price table for West Marches outpost facility upgrades (TASK-0786).

Each upgrade spends the listed gold and materials from the outpost stored resources.
The stored gold lives under the `gold` key. Prices are modest defaults. Operators tune
them here, then update the how-to guide.
Governed by ADR-0003 and Hard Invariant 2.
"""

from __future__ import annotations

from typing import Any

OUTPOST_FACILITY_PRICES: dict[str, dict[int, dict[str, Any]]] = {
    "alchemical_workshop": {
        1: {"cost_gold": 20, "cost_materials": {"timber": 3}},
        2: {"cost_gold": 40, "cost_materials": {"timber": 8}},
        3: {"cost_gold": 100, "cost_materials": {"timber": 20, "stone": 10}},
    },
    "watchtower": {
        1: {"cost_gold": 20, "cost_materials": {"timber": 3}},
        2: {"cost_gold": 40, "cost_materials": {"timber": 8}},
        3: {"cost_gold": 100, "cost_materials": {"timber": 20, "stone": 10}},
    },
    "trading_post": {
        1: {"cost_gold": 25, "cost_materials": {"timber": 4}},
        2: {"cost_gold": 50, "cost_materials": {"timber": 8, "stone": 4}},
        3: {"cost_gold": 120, "cost_materials": {"timber": 20, "stone": 10}},
    },
    "arcane_forge": {
        1: {"cost_gold": 30, "cost_materials": {"stone": 4}},
        2: {"cost_gold": 60, "cost_materials": {"stone": 8}},
        3: {"cost_gold": 150, "cost_materials": {"stone": 15, "timber": 15}},
    },
    "herbal_rack": {
        1: {"cost_gold": 20, "cost_materials": {"timber": 3}},
        2: {"cost_gold": 40, "cost_materials": {"timber": 8}},
        3: {"cost_gold": 100, "cost_materials": {"timber": 15, "stone": 8}},
    },
}

MAX_FACILITY_TIER = 3


class InsufficientOutpostResources(ValueError):
    """Raised when the outpost stored resources cannot pay the tier price. Answers 409."""


def stored_shortfalls(stored: dict[str, int], gold: int, materials: dict[str, int]) -> list[str]:
    """Describe each gold or material amount that the outpost stores cannot cover."""
    problems: list[str] = []
    held_gold = stored.get("gold", 0)
    if gold > held_gold:
        problems.append(f"gold: need {gold}, store holds {held_gold}")
    for mat, qty in materials.items():
        held = stored.get(mat, 0)
        if qty > held:
            problems.append(f"{mat}: need {qty}, store holds {held}")
    return problems


__all__ = [
    "MAX_FACILITY_TIER",
    "OUTPOST_FACILITY_PRICES",
    "InsufficientOutpostResources",
    "stored_shortfalls",
]
