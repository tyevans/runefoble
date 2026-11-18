"""Tabletop 3D physics simulation and collision integration router."""

from __future__ import annotations

import logging
from typing import Annotated

from board_state.authz import PLAY, require_campaign_permission, require_token_move
from board_state.dependencies import get_board, get_current_user_id, get_event_bus, repo
from board_state.events import publish_board_events
from board_state.models import (
    KnockbackRequest,
    KnockbackResponse,
    SimulateThrowRequest,
    SimulateThrowResponse,
)
from board_state.physics import apply_dice_throw, apply_token_knockback
from board_state.realtime import board_ws_manager
from fastapi import APIRouter, Depends, HTTPException
from runefoble_platform.event_publish import deliver_best_effort

logger = logging.getLogger("runefoble.board_state.routers.physics")
router = APIRouter(tags=["physics"], dependencies=[Depends(get_current_user_id)])


@router.post(
    "/api/v1/boards/{board_id}/physics/simulate-throw", response_model=SimulateThrowResponse
)
async def simulate_throw_endpoint(
    board_id: str, req: SimulateThrowRequest, user_id: Annotated[str, Depends(get_current_user_id)]
) -> SimulateThrowResponse:
    """Simulate a 3D physical tumbling dice throw with gravity, floor/wall bounces, and resting face."""
    board = await get_board(board_id)
    await require_campaign_permission(user_id, board_id, PLAY)
    try:
        resp = apply_dice_throw(
            board,
            dice_type=req.dice_type,
            origin=(req.origin_x, req.origin_y, req.origin_z),
            velocity=(req.velocity_x, req.velocity_y, req.velocity_z),
            seed=req.seed,
            dice_id=req.dice_id,
            restitution=req.restitution,
            friction=req.friction,
            target_face_value=req.target_face_value or req.face_value,
        )
        bus = get_event_bus()
        uncommitted = list(board.uncommitted_events)
        await repo.save(board)

        await deliver_best_effort(
            f"board_ws:{board_id}",
            "dice_settled",
            board_ws_manager.broadcast(
                board_id,
                {
                    "type": "dice_settled",
                    "action": "simulate_throw",
                    "status": "settled",
                    "dice": resp.model_dump(),
                },
            ),
        )
        if bus is not None:
            await publish_board_events(bus, uncommitted)
        return resp
    except ValueError as e:
        raise HTTPException(
            status_code=404 if "not found" in str(e).lower() else 400, detail=str(e)
        ) from e
    except Exception as e:
        logger.exception("Failed to simulate throw")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/api/v1/boards/{board_id}/physics/knockback", response_model=KnockbackResponse)
async def knockback_endpoint(
    board_id: str, req: KnockbackRequest, user_id: Annotated[str, Depends(get_current_user_id)]
) -> KnockbackResponse:
    """Apply physical knockback impulse to a miniature token, halting upon wall or elevation collisions."""
    board = await get_board(board_id)
    await require_token_move(user_id, board_id, req.token_id)
    try:
        resp = apply_token_knockback(
            board,
            token_id=req.token_id,
            direction_x=req.direction_x,
            direction_y=req.direction_y,
            distance_ft=req.distance_ft,
            mass=req.mass,
        )
        bus = get_event_bus()
        uncommitted = list(board.uncommitted_events)
        await repo.save(board)

        await deliver_best_effort(
            f"board_ws:{board_id}",
            "token_knockback",
            board_ws_manager.broadcast(
                board_id,
                {
                    "type": "token_knockback",
                    "action": "knockback",
                    "status": "settled",
                    "knockback": resp.model_dump(),
                },
            ),
        )
        if bus is not None:
            await publish_board_events(bus, uncommitted)
        return resp
    except ValueError as e:
        raise HTTPException(
            status_code=404 if "not found" in str(e).lower() else 400, detail=str(e)
        ) from e
    except Exception as e:
        logger.exception("Failed to execute token knockback")
        raise HTTPException(status_code=500, detail=str(e)) from e
