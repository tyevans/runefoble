"""Session lifecycle, participation, turns, and dice roll routes."""

from __future__ import annotations

import contextlib
from uuid import UUID, uuid4

from fastapi import APIRouter, Header, HTTPException
from game_session.aggregate import GameSessionAggregate, GameSessionState
from game_session.dependencies import (
    STREAM_SESSION,
    get_event_bus,
    get_spicedb_client,
    repo,
)
from game_session.models import (
    CreateSessionRequest,
    HotSwapRequest,
    HotSwapResponse,
    JoinSessionRequest,
    LeaveSessionRequest,
    RollDiceRequest,
    RollDiceResponse,
)
from runefoble_events.events import (
    CharacterControlTransferred,
    DiceRolled,
    SessionStarted,
)
from runefoble_platform.dice import parse_and_roll

router = APIRouter(tags=["session"])


@router.post("/api/v1/sessions/create", response_model=GameSessionState)
async def create_session(req: CreateSessionRequest) -> GameSessionState:
    """Create a new event-sourced game session."""
    session_id = uuid4()
    session = GameSessionAggregate(session_id)
    session.create(campaign_id=req.campaign_id, title=req.title, dm_id=req.dm_id)
    await repo.save(session)
    return session.state


@router.get("/api/v1/sessions/{session_id}", response_model=GameSessionState)
async def get_session(session_id: UUID) -> GameSessionState:
    """Load session state reconstituted from the event stream."""
    try:
        session = await repo.load(session_id)
        return session.state
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Session not found: {e}") from e


@router.post("/api/v1/sessions/{session_id}/start", response_model=GameSessionState)
async def start_session(session_id: UUID) -> GameSessionState:
    """Transition session from lobby to active."""
    try:
        session = await repo.load(session_id)
        session.start()
        await repo.save(session)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    bus = get_event_bus()
    if bus:
        with contextlib.suppress(Exception):
            await bus.publish_event(
                STREAM_SESSION,
                SessionStarted(
                    aggregate_id=session_id,
                    started_at_turn=session.state.current_turn,
                ),
            )

    return session.state


@router.post("/api/v1/sessions/{session_id}/join", response_model=GameSessionState)
async def join_session(session_id: UUID, req: JoinSessionRequest) -> GameSessionState:
    """Record player entering session."""
    try:
        session = await repo.load(session_id)
        session.join_player(
            player_id=req.player_id,
            character_id=req.character_id,
            character_name=req.character_name,
            character_class=req.character_class,
        )
        await repo.save(session)
        return session.state
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/api/v1/sessions/{session_id}/leave", response_model=GameSessionState)
async def leave_session(session_id: UUID, req: LeaveSessionRequest) -> GameSessionState:
    """Record player absence, marking character for AI stand-in."""
    try:
        session = await repo.load(session_id)
        session.leave_player(player_id=req.player_id, reason=req.reason)
        await repo.save(session)
        return session.state
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/api/v1/sessions/{session_id}/hot-swap", response_model=HotSwapResponse)
async def hot_swap_session(
    session_id: UUID,
    req: HotSwapRequest,
    x_user_id: str | None = Header(None, alias="x-user-id"),
) -> HotSwapResponse:
    """Hands off active turn control from AI stand-in to authenticating player mid-session."""
    spicedb = get_spicedb_client()
    if x_user_id:
        allowed = await spicedb.check_permission(
            resource_type="character",
            resource_id=str(req.character_id),
            permission="edit",
            subject_type="user",
            subject_id=x_user_id,
        )
        if not allowed:
            allowed = await spicedb.check_permission(
                resource_type="game_session",
                resource_id=str(session_id),
                permission="participate",
                subject_type="user",
                subject_id=x_user_id,
            )
        if not allowed:
            raise HTTPException(
                status_code=403,
                detail=f"User '{x_user_id}' does not have permission to take control of character '{req.character_id}'",
            )

    try:
        session = await repo.load(session_id)
        session.hot_swap_character(player_id=req.player_id, character_id=req.character_id)
        await repo.save(session)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    event = CharacterControlTransferred(
        aggregate_id=session_id,
        session_id=str(session_id),
        character_id=str(req.character_id),
        player_id=req.player_id,
        previous_controller="ai_stand_in",
        new_controller="player",
    )
    bus = get_event_bus()
    if bus:
        with contextlib.suppress(Exception):
            await bus.publish_event(STREAM_SESSION, event)

    return HotSwapResponse(
        session_id=session_id,
        character_id=req.character_id,
        player_id=req.player_id,
        previous_controller="ai_stand_in",
        new_controller="player",
        current_turn=session.state.current_turn,
        in_combat=session.state.in_combat,
        combat_round=session.state.combat_round,
        combat_active_id=session.state.combat_active_id,
        session_state=session.state,
    )


@router.post("/api/v1/sessions/{session_id}/next-turn", response_model=GameSessionState)
async def advance_turn(session_id: UUID) -> GameSessionState:
    """Advance to the next turn in the session."""
    try:
        session = await repo.load(session_id)
        session.advance_turn()
        await repo.save(session)
        return session.state
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/api/v1/sessions/{session_id}/roll", response_model=RollDiceResponse)
async def roll_dice_session(
    session_id: UUID, req: RollDiceRequest | None = None
) -> RollDiceResponse:
    """Evaluate a dice roll, emit a DiceRolled domain event, and record to the session."""
    req_data = req or RollDiceRequest()
    result = parse_and_roll(req_data.formula)

    event = DiceRolled(
        aggregate_id=session_id,
        session_id=str(session_id),
        roller_id=req_data.roller_id,
        roller_name=req_data.roller_name,
        formula=req_data.formula,
        total=result["total"],
        rolls=result["rolls"],
        is_crit=result.get("is_crit", False),
        is_fumble=result.get("is_fumble", False),
    )

    bus = get_event_bus()
    if bus:
        with contextlib.suppress(Exception):
            await bus.publish_event(STREAM_SESSION, event)

    return RollDiceResponse(
        session_id=session_id,
        roller_id=req_data.roller_id,
        roller_name=req_data.roller_name,
        formula=req_data.formula,
        total=result["total"],
        rolls=result["rolls"],
        is_crit=result.get("is_crit", False),
        is_fumble=result.get("is_fumble", False),
        roll_type=req_data.roll_type,
    )
