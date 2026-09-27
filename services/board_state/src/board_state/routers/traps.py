"""Secret DM spatial traps, stage triggers, and map switcher REST router."""

from __future__ import annotations

import logging
from typing import Annotated

from board_state.dependencies import (
    check_user_can_manage_traps,
    check_user_can_switch_map,
    check_user_can_view_secret_layer,
    get_current_user_id,
    get_event_bus,
    get_or_create_board,
    repo,
)
from board_state.traps import (
    CreateTrapRequest,
    SecretTrapState,
    SwitchMapRequest,
    SwitchMapResponse,
    TrapListResponse,
    perform_map_switch,
)
from fastapi import APIRouter, Depends, HTTPException, Query, status

logger = logging.getLogger("runefoble.board_state.routers.traps")
router = APIRouter(tags=["traps"])


async def _publish_events(bus: object, events: list[object]) -> None:
    for evt in events:
        try:
            if hasattr(bus, "publish_event"):
                await bus.publish_event("runefoble.events.board", evt)
            elif hasattr(bus, "publish"):
                await bus.publish(evt)
        except Exception:
            pass


@router.post("/api/v1/boards/{board_id}/traps", response_model=SecretTrapState, status_code=201)
@router.post("/boards/{board_id}/traps", response_model=SecretTrapState, status_code=201)
async def create_trap(
    board_id: str,
    req: CreateTrapRequest,
    user_id: Annotated[str | None, Depends(get_current_user_id)] = None,
    campaign_id: str | None = Query(default=None),
) -> SecretTrapState:
    """Create a secret DM trap or trigger on the tactical board (DM only)."""
    if not await check_user_can_manage_traps(user_id, board_id, campaign_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: DM permissions required to create secret traps",
        )

    board = await get_or_create_board(board_id)
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
    if bus and uncommitted:
        await _publish_events(bus, uncommitted)

    return board.state.traps[tid]


@router.get("/api/v1/boards/{board_id}/traps", response_model=TrapListResponse)
@router.get("/boards/{board_id}/traps", response_model=TrapListResponse)
async def list_traps(
    board_id: str,
    user_id: Annotated[str | None, Depends(get_current_user_id)] = None,
    campaign_id: str | None = Query(default=None),
) -> TrapListResponse:
    """Retrieve traps on the board, filtering out secret traps for non-DM players."""
    board = await get_or_create_board(board_id)
    can_view_secret = await check_user_can_view_secret_layer(user_id, board_id, campaign_id)

    all_traps = list(board.state.traps.values())
    visible = all_traps if can_view_secret else [t for t in all_traps if not t.is_secret]

    return TrapListResponse(board_id=board_id, traps=visible, total=len(visible))


@router.post("/api/v1/boards/{board_id}/switch-map", response_model=SwitchMapResponse)
@router.post("/boards/{board_id}/switch-map", response_model=SwitchMapResponse)
async def switch_map_endpoint(
    board_id: str,
    req: SwitchMapRequest,
    user_id: Annotated[str | None, Depends(get_current_user_id)] = None,
    campaign_id: str | None = Query(default=None),
) -> SwitchMapResponse:
    """Transition board to new battlemap and teleport party tokens in a single transaction (DM only)."""
    if not await check_user_can_switch_map(user_id, board_id, campaign_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: DM permissions required to switch battlemaps",
        )

    board = await get_or_create_board(board_id)
    resp = perform_map_switch(board, req, initiated_by=user_id)

    bus = get_event_bus()
    uncommitted = list(board.uncommitted_events)
    await repo.save(board)
    if bus and uncommitted:
        await _publish_events(bus, uncommitted)

    return resp


@router.post("/api/v1/boards/{board_id}/traps/{trap_id}/disarm")
@router.post("/boards/{board_id}/traps/{trap_id}/disarm")
async def disarm_trap_endpoint(
    board_id: str,
    trap_id: str,
    user_id: Annotated[str | None, Depends(get_current_user_id)] = None,
) -> dict[str, str]:
    """Disarm a trap on the board."""
    board = await get_or_create_board(board_id)
    if trap_id not in board.state.traps:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trap not found")

    board.disarm_trap(trap_id, disarmed_by=user_id)
    bus = get_event_bus()
    uncommitted = list(board.uncommitted_events)
    await repo.save(board)
    if bus and uncommitted:
        await _publish_events(bus, uncommitted)

    return {"trap_id": trap_id, "status": "disarmed"}
