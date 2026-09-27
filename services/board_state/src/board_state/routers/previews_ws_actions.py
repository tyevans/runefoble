"""Tactical board WebSocket message handlers for token actions and AoE templates."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from board_state.aggregate import BoardAggregate
from board_state.aoe import evaluate_aoe_targets
from board_state.dependencies import repo
from board_state.preview import board_ws_manager


async def _handle_token_action(
    session_id: str, action: str, data: dict[str, Any], board: BoardAggregate
) -> None:
    token_id = data.get("token_id")
    action_name = data.get("token_action") or data.get("action_name") or data.get("name") or "dodge"
    if not token_id:
        return
    targets = list(data.get("target_token_ids") or [])
    if data.get("target_token_id") and data.get("target_token_id") not in targets:
        targets.append(data.get("target_token_id"))
    board.execute_token_action(
        token_id=token_id,
        action=action_name,
        target_token_id=data.get("target_token_id"),
        target_token_ids=data.get("target_token_ids"),
        details=data.get("details"),
        initiated_by=data.get("initiated_by", "player"),
    )
    await repo.save(board)
    await board_ws_manager.broadcast(
        session_id,
        {
            "type": "token_action_executed",
            "action": action_name.lower(),
            "token_id": token_id,
            "target_token_ids": targets,
            "details": data.get("details", {}),
            "initiated_by": data.get("initiated_by", "player"),
        },
    )


async def _handle_aoe_msg(
    session_id: str, action: str, data: dict[str, Any], board: BoardAggregate
) -> None:
    is_place = action == "aoe_place"
    tid = data.get("template_id") or str(uuid4())
    ev = evaluate_aoe_targets(
        tokens=board.state.tokens,
        cols=board.state.cols,
        rows=board.state.rows,
        shape=data.get("shape", "cone"),
        origin_x=float(data.get("origin_x", 0)),
        origin_y=float(data.get("origin_y", 0)),
        direction_deg=float(data.get("direction_deg", 0)),
        radius_ft=float(data["radius_ft"]) if data.get("radius_ft") is not None else None,
        length_ft=float(data["length_ft"]) if data.get("length_ft") is not None else None,
        width_ft=float(data["width_ft"]) if data.get("width_ft") is not None else 5.0,
        grid_type=data.get("grid_type", "square"),
        template_id=tid,
        caster_token_id=data.get("caster_token_id"),
        spell_name=data.get("spell_name"),
    )
    if is_place:
        board.place_aoe_template(
            template_id=tid,
            shape=ev.shape,
            origin_x=ev.origin_x,
            origin_y=ev.origin_y,
            direction_deg=ev.direction_deg,
            radius_ft=ev.radius_ft,
            length_ft=ev.length_ft,
            width_ft=ev.width_ft,
            caster_token_id=ev.caster_token_id,
            spell_name=ev.spell_name,
            affected_token_ids=ev.affected_token_ids,
            affected_cells=ev.affected_cells,
        )
        await repo.save(board)
    mtype = "aoe_template_placed" if is_place else "aoe_preview"
    await board_ws_manager.broadcast(
        session_id,
        {"type": mtype, "action": mtype, "session_id": session_id, "template": ev.model_dump()},
    )


async def handle_ws_action(
    session_id: str, action: str, data: dict[str, Any], board: BoardAggregate
) -> bool:
    """Handle combat actions and AoE templates over WebSocket."""
    if action in ("token_action", "radial_action"):
        await _handle_token_action(session_id, action, data, board)
        return True
    if action in ("aoe_preview", "aoe_evaluate", "aoe_place"):
        await _handle_aoe_msg(session_id, action, data, board)
        return True
    return False


__all__ = ["handle_ws_action"]
