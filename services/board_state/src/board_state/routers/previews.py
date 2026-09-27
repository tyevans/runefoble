"""Kinematics, route preview calculation, and WebSocket streaming router."""

from __future__ import annotations

from uuid import uuid4

from board_state.aoe import evaluate_aoe_targets
from board_state.dependencies import get_or_create_board, repo
from board_state.preview import (
    PreviewMoveRequest,
    PreviewMoveResponse,
    board_ws_manager,
    compute_kinematic_route_preview,
)
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

router = APIRouter(tags=["previews"])


@router.post(
    "/api/v1/boards/{session_id}/tokens/{token_id}/preview", response_model=PreviewMoveResponse
)
async def preview_token_move(session_id: str, token_id: str, req: PreviewMoveRequest):
    """Compute waypoint trajectory, 5-ft increments, terrain penalties, and hazard warnings."""
    board = await get_or_create_board(session_id)
    try:
        return compute_kinematic_route_preview(
            board_aggregate=board,
            token_id=token_id,
            to_x=req.to_x,
            to_y=req.to_y,
            from_x=req.from_x,
            from_y=req.from_y,
            movement_budget=req.movement_budget,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/api/v1/boards/{session_id}/preview", response_model=PreviewMoveResponse)
@router.post("/api/v1/boards/{session_id}/preview-move", response_model=PreviewMoveResponse)
async def preview_move(session_id: str, req: PreviewMoveRequest):
    if not req.token_id:
        raise HTTPException(status_code=400, detail="token_id is required")
    return await preview_token_move(session_id, req.token_id, req)


@router.websocket("/ws/boards/{session_id}")
async def board_websocket(websocket: WebSocket, session_id: str):
    """Real-time tactical board WebSocket stream for kinematic dragging and ghost previews."""
    await board_ws_manager.connect(session_id, websocket)
    try:
        await websocket.send_json(
            {
                "type": "connected",
                "session_id": session_id,
                "message": "Connected to tactical board real-time stream.",
            }
        )
        while True:
            data = await websocket.receive_json()
            action = data.get("action") or data.get("type") or "unknown"

            if action in (
                "preview_move",
                "ghost_preview",
                "speech_intent",
                "SpeechIntentParsed",
            ):
                token_id = data.get("token_id")
                speaker_name = data.get("speaker_name")
                board = await get_or_create_board(session_id)

                if not token_id and speaker_name:
                    for tok in board.state.tokens.values():
                        if tok.name.lower() == speaker_name.lower():
                            token_id = tok.token_id
                            break

                to_x = data.get("to_x")
                to_y = data.get("to_y")
                if token_id and to_x is not None and to_y is not None:
                    preview = compute_kinematic_route_preview(
                        board_aggregate=board,
                        token_id=token_id,
                        to_x=int(to_x),
                        to_y=int(to_y),
                        from_x=data.get("from_x"),
                        from_y=data.get("from_y"),
                        movement_budget=data.get("movement_budget"),
                    )
                    await board_ws_manager.broadcast(
                        session_id,
                        {
                            "type": "ghost_preview",
                            "action": "ghost_preview",
                            "status": "staged",
                            "session_id": session_id,
                            "speaker_name": speaker_name,
                            "raw_transcript": data.get("raw_transcript"),
                            "preview": preview.model_dump(),
                            "timeout_seconds": data.get("timeout_seconds", 15),
                        },
                    )

            elif action in ("confirm_move", "confirm_ghost", "confirm_intent"):
                token_id = data.get("token_id")
                to_x = data.get("to_x")
                to_y = data.get("to_y")
                board = await get_or_create_board(session_id)
                if token_id and to_x is not None and to_y is not None:
                    cost, hazard_trig, dmg_dice = board.move_token(
                        token_id=token_id,
                        to_x=int(to_x),
                        to_y=int(to_y),
                        initiated_by=data.get("initiated_by", "player"),
                        movement_budget=data.get("movement_budget"),
                    )
                    await repo.save(board)
                    tok = board.state.tokens[token_id]
                    await board_ws_manager.broadcast(
                        session_id,
                        {
                            "type": "token_moved",
                            "action": "token_moved",
                            "status": "confirmed",
                            "session_id": session_id,
                            "token_id": token_id,
                            "name": tok.name,
                            "x": tok.x,
                            "y": tok.y,
                            "movement_cost": cost,
                            "hazard_triggered": hazard_trig,
                            "damage_dice": dmg_dice,
                            "active_hazard": tok.active_hazard,
                        },
                    )

            elif action in ("cancel_preview", "cancel_ghost"):
                await board_ws_manager.broadcast(
                    session_id,
                    {
                        "type": "preview_cancelled",
                        "action": "preview_cancelled",
                        "status": "cancelled",
                        "session_id": session_id,
                        "token_id": data.get("token_id"),
                    },
                )
            elif action in ("token_action", "radial_action"):
                token_id = data.get("token_id")
                action_name = (
                    data.get("token_action")
                    or data.get("action_name")
                    or data.get("name")
                    or "dodge"
                )
                board = await get_or_create_board(session_id)
                if token_id:
                    board.execute_token_action(
                        token_id=token_id,
                        action=action_name,
                        target_token_id=data.get("target_token_id"),
                        target_token_ids=data.get("target_token_ids"),
                        details=data.get("details"),
                        initiated_by=data.get("initiated_by", "player"),
                    )
                    await repo.save(board)
                    all_targets = list(data.get("target_token_ids") or [])
                    if (
                        data.get("target_token_id")
                        and data.get("target_token_id") not in all_targets
                    ):
                        all_targets.append(data.get("target_token_id"))
                    await board_ws_manager.broadcast(
                        session_id,
                        {
                            "type": "token_action_executed",
                            "action": action_name.lower(),
                            "token_id": token_id,
                            "target_token_ids": all_targets,
                            "details": data.get("details", {}),
                            "initiated_by": data.get("initiated_by", "player"),
                        },
                    )

            elif action in ("aoe_preview", "aoe_evaluate"):
                board = await get_or_create_board(session_id)
                evaluated = evaluate_aoe_targets(
                    tokens=board.state.tokens,
                    cols=board.state.cols,
                    rows=board.state.rows,
                    shape=data.get("shape", "cone"),
                    origin_x=float(data.get("origin_x", 0)),
                    origin_y=float(data.get("origin_y", 0)),
                    direction_deg=float(data.get("direction_deg", 0)),
                    radius_ft=float(data["radius_ft"])
                    if data.get("radius_ft") is not None
                    else None,
                    length_ft=float(data["length_ft"])
                    if data.get("length_ft") is not None
                    else None,
                    width_ft=float(data["width_ft"]) if data.get("width_ft") is not None else 5.0,
                    grid_type=data.get("grid_type", "square"),
                    template_id=data.get("template_id", str(uuid4())),
                    caster_token_id=data.get("caster_token_id"),
                    spell_name=data.get("spell_name"),
                )
                await board_ws_manager.broadcast(
                    session_id,
                    {
                        "type": "aoe_preview",
                        "action": "aoe_preview",
                        "session_id": session_id,
                        "template": evaluated.model_dump(),
                    },
                )

            elif action == "aoe_place":
                board = await get_or_create_board(session_id)
                template_id = data.get("template_id") or str(uuid4())
                evaluated = evaluate_aoe_targets(
                    tokens=board.state.tokens,
                    cols=board.state.cols,
                    rows=board.state.rows,
                    shape=data.get("shape", "cone"),
                    origin_x=float(data.get("origin_x", 0)),
                    origin_y=float(data.get("origin_y", 0)),
                    direction_deg=float(data.get("direction_deg", 0)),
                    radius_ft=float(data["radius_ft"])
                    if data.get("radius_ft") is not None
                    else None,
                    length_ft=float(data["length_ft"])
                    if data.get("length_ft") is not None
                    else None,
                    width_ft=float(data["width_ft"]) if data.get("width_ft") is not None else 5.0,
                    grid_type=data.get("grid_type", "square"),
                    template_id=template_id,
                    caster_token_id=data.get("caster_token_id"),
                    spell_name=data.get("spell_name"),
                )
                board.place_aoe_template(
                    template_id=template_id,
                    shape=evaluated.shape,
                    origin_x=evaluated.origin_x,
                    origin_y=evaluated.origin_y,
                    direction_deg=evaluated.direction_deg,
                    radius_ft=evaluated.radius_ft,
                    length_ft=evaluated.length_ft,
                    width_ft=evaluated.width_ft,
                    caster_token_id=evaluated.caster_token_id,
                    spell_name=evaluated.spell_name,
                    affected_token_ids=evaluated.affected_token_ids,
                    affected_cells=evaluated.affected_cells,
                )
                await repo.save(board)
                await board_ws_manager.broadcast(
                    session_id,
                    {
                        "type": "aoe_template_placed",
                        "action": "aoe_template_placed",
                        "session_id": session_id,
                        "template": evaluated.model_dump(),
                    },
                )
            else:
                await board_ws_manager.broadcast(session_id, data)

    except WebSocketDisconnect:
        board_ws_manager.disconnect(session_id, websocket)
