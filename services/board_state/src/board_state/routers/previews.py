"""Kinematics, route preview calculation, and WebSocket streaming router."""

from __future__ import annotations

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
            else:
                await board_ws_manager.broadcast(session_id, data)
    except WebSocketDisconnect:
        board_ws_manager.disconnect(session_id, websocket)
