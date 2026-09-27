"""Atomic battlemap switching and multi-token party teleportation handler."""

from __future__ import annotations

from typing import TYPE_CHECKING

from board_state.traps.models import SwitchMapRequest, SwitchMapResponse

if TYPE_CHECKING:
    from board_state.aggregate import BoardAggregate


def perform_map_switch(
    board: BoardAggregate,
    req: SwitchMapRequest,
    initiated_by: str | None = None,
) -> SwitchMapResponse:
    """Execute battlemap transition and teleport party tokens in a single event."""
    previous_map_id = getattr(board.state, "current_map_id", None)
    cols = req.cols or board.state.cols
    rows = req.rows or board.state.rows

    validated_teleports: dict[str, list[int]] = {}
    for tid, coords in req.token_teleports.items():
        if tid in board.state.tokens and len(coords) >= 2:
            validated_teleports[tid] = [int(coords[0]), int(coords[1])]

    board.switch_battlemap(
        new_map_id=req.new_map_id,
        cols=cols,
        rows=rows,
        background_asset_id=req.background_asset_id,
        background_image_url=req.background_image_url,
        token_teleports=validated_teleports,
        initiated_by=initiated_by,
        clear_existing_traps=req.clear_existing_traps,
    )

    return SwitchMapResponse(
        board_id=str(board.aggregate_id),
        previous_map_id=previous_map_id,
        new_map_id=req.new_map_id,
        cols=cols,
        rows=rows,
        background_asset_id=req.background_asset_id,
        background_image_url=req.background_image_url,
        teleported_tokens=validated_teleports,
        status="switched",
    )
