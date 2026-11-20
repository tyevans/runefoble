"""Destination cell of a spoken move (TASK-0942, ADR-0015 a, ADR-0022 c).

The Watcher reads the destination that the intent carries. It never invents an origin or a
destination. A failed rule is an explicit 4xx, and no preview is staged. The keys are read in
this order:

1. A named target token (`target_token`, `target_token_name`, `target_token_id`, `target`).
   The destination is the free cell next to that token that is nearest to the origin.
2. Coordinates (`to_x`/`to_y` from the grammar, or `target_x`/`target_y` from the worker).
3. A distance move (`dx`/`dy`), computed from the origin inside the grid.
"""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException
from the_watcher.spatial import chebyshev_steps

NAME_KEYS = ("target_token", "target_token_name", "target")
ID_KEY = "target_token_id"
COORDINATE_KEYS = (("to_x", "to_y"), ("target_x", "target_y"))
NEIGHBOUR_OFFSETS = tuple((dx, dy) for dy in (-1, 0, 1) for dx in (-1, 0, 1) if (dx, dy) != (0, 0))


def named_target(parameters: dict[str, Any]) -> tuple[set[str], str | None]:
    """Return the casefolded names and the token id that the intent names. Both may be empty."""
    names = {str(parameters[key]).casefold() for key in NAME_KEYS if parameters.get(key)}
    token_id = parameters.get(ID_KEY) or None
    return names, token_id


def coordinate_target(parameters: dict[str, Any]) -> tuple[int, int] | None:
    """Return the cell that the intent gives in coordinates, or None when it gives none."""
    for x_key, y_key in COORDINATE_KEYS:
        x, y = parameters.get(x_key), parameters.get(y_key)
        if x is not None and y is not None:
            return int(x), int(y)
    return None


def check_origin(from_x: int | None, from_y: int | None) -> tuple[int, int]:
    """Return the origin. A missing coordinate is a client error (422). It is never 0."""
    missing = [name for name, value in (("from_x", from_x), ("from_y", from_y)) if value is None]
    if missing or from_x is None or from_y is None:
        raise HTTPException(
            status_code=422,
            detail=f"A spoken move needs {' and '.join(missing)}. The Watcher stages nothing.",
        )
    return from_x, from_y


def check_in_grid(cell: tuple[int, int], cols: int, rows: int) -> tuple[int, int]:
    """Return the cell when it lies inside the grid. Otherwise raise 422."""
    x, y = cell
    if not (0 <= x < cols and 0 <= y < rows):
        raise HTTPException(
            status_code=422,
            detail=f"Destination ({x}, {y}) is outside the {cols} x {rows} grid.",
        )
    return cell


def _matches(token: dict[str, Any], names: set[str], token_id: str | None) -> bool:
    name = str(token.get("name") or "").casefold()
    return (name in names) or (token_id is not None and token.get("token_id") == token_id)


def nearest_free_neighbour(
    target_token: dict[str, Any],
    tokens: list[dict[str, Any]],
    origin: tuple[int, int],
    cols: int,
    rows: int,
) -> tuple[int, int]:
    """Return the free cell next to `target_token` that is nearest to `origin`.

    Distance is grid distance (a diagonal step counts as one step, as in the 5-foot grid).
    A tie goes to the lower `y`, then the lower `x`. No free cell raises 409.
    """
    occupied = {(tok.get("x"), tok.get("y")) for tok in tokens}
    tx, ty = int(target_token["x"]), int(target_token["y"])
    candidates = [
        (tx + dx, ty + dy)
        for dx, dy in NEIGHBOUR_OFFSETS
        if 0 <= tx + dx < cols and 0 <= ty + dy < rows and (tx + dx, ty + dy) not in occupied
    ]
    if not candidates:
        raise HTTPException(
            status_code=409,
            detail=f"No free cell next to '{target_token.get('name')}'. The Watcher stages nothing.",
        )
    return min(candidates, key=lambda cell: (chebyshev_steps(origin, cell), cell[1], cell[0]))


def resolve_named_target(
    names: set[str],
    token_id: str | None,
    tokens: list[dict[str, Any]],
    origin: tuple[int, int],
    cols: int,
    rows: int,
) -> tuple[int, int]:
    """Resolve a named target to a free neighbour. No token matches: 422. Two or more: 409."""
    matched: dict[str, dict[str, Any]] = {}
    for token in tokens:
        if _matches(token, names, token_id):
            matched[str(token.get("token_id"))] = token
    if not matched:
        label = token_id or ", ".join(sorted(names))
        raise HTTPException(
            status_code=422,
            detail=f"No token on the board matches '{label}'. The Watcher stages nothing.",
        )
    if len(matched) > 1:
        raise HTTPException(
            status_code=409,
            detail="More than one token matches the target. The Watcher stages nothing.",
        )
    (target,) = matched.values()
    return nearest_free_neighbour(target, tokens, origin, cols, rows)
