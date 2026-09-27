"""Rotatable AoE spell templates placement and spatial evaluation router."""

from __future__ import annotations

import contextlib
import logging
from uuid import uuid4

from board_state.aoe import evaluate_aoe_targets
from board_state.dependencies import get_event_bus, get_or_create_board, repo
from board_state.models import (
    AoEEvaluateRequest,
    AoETemplatePlaceRequest,
    AoETemplateResponse,
    AoETemplateState,
)
from board_state.preview import board_ws_manager
from fastapi import APIRouter, HTTPException

logger = logging.getLogger("runefoble.board_state.routers.aoe")

router = APIRouter(tags=["aoe"])


@router.post("/api/v1/boards/{session_id}/aoe/evaluate", response_model=AoETemplateResponse)
async def evaluate_aoe_template(session_id: str, req: AoEEvaluateRequest):
    """Compute mathematical intersection of cone/sphere/line with grid tokens without saving."""
    board = await get_or_create_board(session_id)
    try:
        response = evaluate_aoe_targets(
            tokens=board.state.tokens,
            cols=board.state.cols,
            rows=board.state.rows,
            shape=req.shape,
            origin_x=req.origin_x,
            origin_y=req.origin_y,
            direction_deg=req.direction_deg,
            radius_ft=req.radius_ft,
            length_ft=req.length_ft,
            width_ft=req.width_ft,
            grid_type=req.grid_type,
            template_id=req.template_id or str(uuid4()),
            caster_token_id=req.caster_token_id,
            spell_name=req.spell_name,
        )
        return response
    except Exception as e:
        logger.exception("Failed to evaluate AoE template")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/api/v1/boards/{session_id}/aoe/place", response_model=AoETemplateResponse)
@router.post("/api/v1/boards/{session_id}/aoe", response_model=AoETemplateResponse)
async def place_aoe_template(session_id: str, req: AoETemplatePlaceRequest):
    """Place and persist an AoE spell template on the board, emitting AoETemplatePlaced."""
    board = await get_or_create_board(session_id)
    try:
        template_id = req.template_id or str(uuid4())
        evaluated = evaluate_aoe_targets(
            tokens=board.state.tokens,
            cols=board.state.cols,
            rows=board.state.rows,
            shape=req.shape,
            origin_x=req.origin_x,
            origin_y=req.origin_y,
            direction_deg=req.direction_deg,
            radius_ft=req.radius_ft,
            length_ft=req.length_ft,
            width_ft=req.width_ft,
            grid_type=req.grid_type,
            template_id=template_id,
            caster_token_id=req.caster_token_id,
            spell_name=req.spell_name,
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

        # Broadcast via WebSocket
        with contextlib.suppress(Exception):
            await board_ws_manager.broadcast(
                session_id,
                {
                    "type": "aoe_template_placed",
                    "template": evaluated.model_dump(),
                },
            )

        # Publish to event bus if available
        bus = get_event_bus()
        if bus and board.uncommitted_events:
            with contextlib.suppress(Exception):
                await bus.publish(board.uncommitted_events[-1])

        return evaluated
    except Exception as e:
        logger.exception("Failed to place AoE template")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/api/v1/boards/{session_id}/aoe", response_model=list[AoETemplateState])
async def list_active_aoe_templates(session_id: str):
    """List all active AoE spell templates currently placed on the board."""
    board = await get_or_create_board(session_id)
    return board.state.active_aoe_templates


@router.delete("/api/v1/boards/{session_id}/aoe/{template_id}")
async def remove_aoe_template(session_id: str, template_id: str):
    """Remove an active AoE template from the board."""
    board = await get_or_create_board(session_id)
    try:
        board.remove_aoe_template(template_id)
        await repo.save(board)
        with contextlib.suppress(Exception):
            await board_ws_manager.broadcast(
                session_id,
                {
                    "type": "aoe_template_removed",
                    "template_id": template_id,
                },
            )
        return {"template_id": template_id, "status": "removed"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
