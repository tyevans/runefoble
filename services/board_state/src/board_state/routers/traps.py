"""Secret DM spatial traps, stage triggers, and map switcher REST router."""

from __future__ import annotations

import logging
from typing import Annotated

from board_state.authz import (
    MANAGE_TRAPS,
    SWITCH_MAP,
    VIEW,
    VIEW_SECRET_LAYER,
    can_on_board,
    require_board_permission,
)
from board_state.dependencies import (
    get_board,
    get_current_user_id,
    get_event_bus,
    repo,
)
from board_state.events import publish_board_events
from board_state.projection import public_traps
from board_state.traps import (
    CreateTrapRequest,
    SecretTrapState,
    SwitchMapRequest,
    SwitchMapResponse,
    TrapListResponse,
    perform_map_switch,
)
from fastapi import APIRouter, Depends, HTTPException, status

logger = logging.getLogger("runefoble.board_state.routers.traps")
router = APIRouter(tags=["traps"], dependencies=[Depends(get_current_user_id)])


@router.post("/api/v1/boards/{board_id}/traps", response_model=SecretTrapState, status_code=201)
@router.post("/boards/{board_id}/traps", response_model=SecretTrapState, status_code=201)
async def create_trap(
    board_id: str,
    req: CreateTrapRequest,
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> SecretTrapState:
    """Create a secret DM trap or trigger on the tactical board. Needs `board.manage_traps`."""
    await require_board_permission(user_id, board_id, MANAGE_TRAPS)

    board = await get_board(board_id)
    tid = board.place_trap(
        name=req.name,
        x=req.x,
        y=req.y,
        trigger_type=req.trigger_type,
        proximity_radius=req.proximity_radius,
        dc_detection=req.dc_detection,
        trap_type=req.trap_type,
        is_secret=req.is_secret,
        damage_dice=req.damage_dice,
        description=req.description,
        effect_payload=req.effect_payload,
        trap_id=req.trap_id,
        created_by=user_id,
    )

    bus = get_event_bus()
    uncommitted = list(board.uncommitted_events)
    await repo.save(board)
    if bus is not None:
        await publish_board_events(bus, uncommitted)

    return board.state.traps[tid]


@router.get("/api/v1/boards/{board_id}/traps", response_model=TrapListResponse)
@router.get("/boards/{board_id}/traps", response_model=TrapListResponse)
async def list_traps(
    board_id: str,
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> TrapListResponse:
    """Retrieve traps on the board. Without `board.view_secret_layer` the secret ones are absent."""
    board = await get_board(board_id)
    await require_board_permission(user_id, board_id, VIEW)
    all_traps = board.state.traps
    if not await can_on_board(user_id, board_id, VIEW_SECRET_LAYER):
        all_traps = public_traps(all_traps)
    visible = list(all_traps.values())

    return TrapListResponse(board_id=board_id, traps=visible, total=len(visible))


@router.post("/api/v1/boards/{board_id}/switch-map", response_model=SwitchMapResponse)
@router.post("/boards/{board_id}/switch-map", response_model=SwitchMapResponse)
async def switch_map_endpoint(
    board_id: str,
    req: SwitchMapRequest,
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> SwitchMapResponse:
    """Switch the battlemap and teleport party tokens in one transaction. Needs `board.switch_map`."""
    await require_board_permission(user_id, board_id, SWITCH_MAP)

    board = await get_board(board_id)
    resp = perform_map_switch(board, req, initiated_by=user_id)

    bus = get_event_bus()
    uncommitted = list(board.uncommitted_events)
    await repo.save(board)
    if bus is not None:
        await publish_board_events(bus, uncommitted)

    return resp


@router.post("/api/v1/boards/{board_id}/traps/{trap_id}/disarm")
@router.post("/boards/{board_id}/traps/{trap_id}/disarm")
async def disarm_trap_endpoint(
    board_id: str,
    trap_id: str,
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> dict[str, str]:
    """Disarm a trap on the board. Needs `board.manage_traps`.

    The trap model has no field that lets a player disarm a trap, so every disarm is DM only.
    """
    await require_board_permission(user_id, board_id, MANAGE_TRAPS)
    board = await get_board(board_id)
    if trap_id not in board.state.traps:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trap not found")

    board.disarm_trap(trap_id, disarmed_by=user_id)
    bus = get_event_bus()
    uncommitted = list(board.uncommitted_events)
    await repo.save(board)
    if bus is not None:
        await publish_board_events(bus, uncommitted)

    return {"trap_id": trap_id, "status": "disarmed"}
