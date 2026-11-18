"""Rotatable AoE template evaluation for board_state.

Containment lives in board_state.geometry. This module adds angle snapping and
turns the geometry result into token and cell lists for the board response.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from board_state.geometry import cell_in_shape, cells_in_shape

if TYPE_CHECKING:
    from board_state.models import AoETemplateResponse, PlacedTokenState


def snap_angle(angle_deg: float, increment: float = 15.0) -> float:
    """Snap an angle in degrees to the nearest increment (default 15 degrees)."""
    if increment <= 0:
        return angle_deg % 360.0
    snapped = round(angle_deg / increment) * increment
    return snapped % 360.0


def evaluate_aoe_targets(
    tokens: dict[str, PlacedTokenState],
    cols: int,
    rows: int,
    shape: str,
    origin_x: int,
    origin_y: int,
    direction_deg: float = 0.0,
    radius_ft: float | None = None,
    length_ft: float | None = None,
    width_ft: float | None = 5.0,
    grid_type: str = "square",
    template_id: str = "",
    caster_token_id: str | None = None,
    spell_name: str | None = None,
) -> AoETemplateResponse:
    """Evaluate target tokens and affected grid cells enclosed by the AoE geometry."""
    from board_state.models import AoETemplateResponse

    snapped_direction = snap_angle(direction_deg)
    geometry = {
        "shape": shape,
        "origin_col": origin_x,
        "origin_row": origin_y,
        "direction_deg": snapped_direction,
        "radius_ft": radius_ft,
        "length_ft": length_ft,
        "width_ft": width_ft,
        "grid_type": grid_type,
    }

    affected_tokens: list[PlacedTokenState] = [
        tok for tok in tokens.values() if cell_in_shape(tok.x, tok.y, **geometry)
    ]
    affected_cells = cells_in_shape(cols=cols, rows=rows, **geometry)

    return AoETemplateResponse(
        template_id=template_id,
        caster_token_id=caster_token_id,
        shape=shape,
        origin_x=origin_x,
        origin_y=origin_y,
        direction_deg=snapped_direction,
        radius_ft=radius_ft,
        length_ft=length_ft,
        width_ft=width_ft,
        spell_name=spell_name,
        affected_token_ids=[tok.token_id for tok in affected_tokens],
        affected_tokens=affected_tokens,
        affected_cells=affected_cells,
    )
