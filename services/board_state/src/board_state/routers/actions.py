"""Token combat actions (Dodge, Dash, Melee/Attack, Disengage, Cast) router."""

from __future__ import annotations

import contextlib
import logging

from board_state.dependencies import get_event_bus, get_or_create_board, repo
from board_state.models import TokenActionRequest, TokenActionResponse
from board_state.preview import board_ws_manager
from fastapi import APIRouter, HTTPException

logger = logging.getLogger("runefoble.board_state.routers.actions")

router = APIRouter(tags=["actions"])


@router.post(
    "/api/v1/boards/{session_id}/tokens/{token_id}/action",
    response_model=TokenActionResponse,
)
async def execute_token_action(session_id: str, token_id: str, req: TokenActionRequest):
    """Execute a contextual tactical action for a token (Dodge, Dash, Melee, Disengage, Cast)."""
    board = await get_or_create_board(session_id)
    try:
        board.execute_token_action(
            token_id=token_id,
            action=req.action,
            target_token_id=req.target_token_id,
            target_token_ids=req.target_token_ids,
            details=req.details,
            initiated_by=req.initiated_by,
        )
        await repo.save(board)

        # Broadcast via WebSocket if manager has active connections
        with contextlib.suppress(Exception):
            await board_ws_manager.broadcast(
                session_id,
                {
                    "type": "token_action_executed",
                    "action": req.action.lower(),
                    "token_id": token_id,
                    "target_token_ids": req.target_token_ids
                    or ([req.target_token_id] if req.target_token_id else []),
                    "details": req.details,
                    "initiated_by": req.initiated_by,
                },
            )

        # Publish to event bus if available
        bus = get_event_bus()
        if bus and board.uncommitted_events:
            with contextlib.suppress(Exception):
                await bus.publish(board.uncommitted_events[-1])

        all_targets = list(req.target_token_ids or [])
        if req.target_token_id and req.target_token_id not in all_targets:
            all_targets.append(req.target_token_id)

        return TokenActionResponse(
            token_id=token_id,
            action=req.action.lower(),
            status="executed",
            target_token_ids=all_targets,
            details=req.details,
            message=f"Action '{req.action}' successfully executed for token {token_id}",
        )
    except ValueError as e:
        raise HTTPException(status_code=404 if "not found" in str(e) else 400, detail=str(e)) from e
    except Exception as e:
        logger.exception("Failed to execute token action")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/api/v1/boards/{session_id}/actions", response_model=TokenActionResponse)
async def execute_action_root(session_id: str, req: TokenActionRequest):
    """Execute action with token_id provided in request body."""
    if not req.token_id:
        raise HTTPException(status_code=400, detail="token_id is required in request body")
    return await execute_token_action(session_id, req.token_id, req)
