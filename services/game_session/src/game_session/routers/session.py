"""Session lifecycle, participation, lobby readiness, turns, and dice roll routes.

Every route saves through the session aggregate. The session repository publishes the
committed events to their streams, so routes do not publish directly.
"""

from __future__ import annotations

from uuid import UUID, uuid4

from eventsource.domain.exceptions import AggregateNotFoundError
from fastapi import APIRouter, Depends, HTTPException
from game_session.aggregate import GameSessionAggregate, GameSessionState
from game_session.character_client import CharacterSheetUnavailableError, release_stand_in
from game_session.dependencies import get_spicedb_client, repo
from game_session.models import (
    CreateSessionRequest,
    HotSwapRequest,
    HotSwapResponse,
    JoinSessionRequest,
    LeaveSessionRequest,
    ReadinessRequest,
    RollDiceRequest,
    RollDiceResponse,
    SelectLobbyCharacterRequest,
)
from game_session.settlement.auth.tokens import CallerId, get_caller_principal
from runefoble_platform.dice import parse_and_roll

router = APIRouter(dependencies=[Depends(get_caller_principal)], tags=["session"])


async def _load_session(session_id: UUID) -> GameSessionAggregate:
    """Load a session by id. Raise 404 when no session has that id."""
    try:
        return await repo.load(session_id)
    except AggregateNotFoundError as e:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}") from e


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
    session = await _load_session(session_id)
    try:
        session.start()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    await repo.save(session)
    return session.state


@router.post("/api/v1/sessions/{session_id}/join", response_model=GameSessionState)
async def join_session(session_id: UUID, req: JoinSessionRequest) -> GameSessionState:
    """Record player entering session."""
    session = await _load_session(session_id)
    try:
        session.join_player(
            player_id=req.player_id,
            character_id=req.character_id,
            character_name=req.character_name,
            character_class=req.character_class,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    await repo.save(session)
    return session.state


@router.post("/api/v1/sessions/{session_id}/leave", response_model=GameSessionState)
async def leave_session(session_id: UUID, req: LeaveSessionRequest) -> GameSessionState:
    """Record player absence, marking character for AI stand-in."""
    session = await _load_session(session_id)
    try:
        session.leave_player(player_id=req.player_id, reason=req.reason)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    await repo.save(session)
    return session.state


@router.post("/api/v1/sessions/{session_id}/lobby/readiness", response_model=GameSessionState)
async def toggle_lobby_readiness(session_id: UUID, req: ReadinessRequest) -> GameSessionState:
    """Record a player's readiness in the session lobby."""
    session = await _load_session(session_id)
    try:
        session.toggle_readiness(player_id=req.player_id, is_ready=req.is_ready)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    await repo.save(session)
    return session.state


@router.post("/api/v1/sessions/{session_id}/lobby/character", response_model=GameSessionState)
async def select_lobby_character(
    session_id: UUID, req: SelectLobbyCharacterRequest
) -> GameSessionState:
    """Record which character a player brings to the session lobby."""
    session = await _load_session(session_id)
    try:
        session.select_lobby_character(player_id=req.player_id, character_id=req.character_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    await repo.save(session)
    return session.state


@router.post("/api/v1/sessions/{session_id}/hot-swap", response_model=HotSwapResponse)
async def hot_swap_session(
    caller_id: CallerId,
    session_id: UUID,
    req: HotSwapRequest,
) -> HotSwapResponse:
    """Hands off active turn control from AI stand-in to authenticating player mid-session."""
    spicedb = get_spicedb_client()
    allowed = await spicedb.check_permission(
        resource_type="character",
        resource_id=str(req.character_id),
        permission="edit",
        subject_type="user",
        subject_id=caller_id,
    )
    if not allowed:
        allowed = await spicedb.check_permission(
            resource_type="game_session",
            resource_id=str(session_id),
            permission="participate",
            subject_type="user",
            subject_id=caller_id,
        )
    if not allowed:
        raise HTTPException(
            status_code=403,
            detail=f"User '{caller_id}' does not have permission to take control of character '{req.character_id}'",
        )

    session = await _load_session(session_id)
    try:
        session.hot_swap_character(player_id=req.player_id, character_id=req.character_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    try:
        await release_stand_in(req.character_id, session_id)
    except CharacterSheetUnavailableError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    await repo.save(session)

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
    session = await _load_session(session_id)
    try:
        session.advance_turn()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    await repo.save(session)
    return session.state


@router.post("/api/v1/sessions/{session_id}/roll", response_model=RollDiceResponse)
async def roll_dice_session(
    session_id: UUID, req: RollDiceRequest | None = None
) -> RollDiceResponse:
    """Evaluate a dice roll and record it on the session aggregate."""
    req_data = req or RollDiceRequest()
    session = await _load_session(session_id)
    result = parse_and_roll(req_data.formula)
    session.record_dice_roll(
        roller_id=req_data.roller_id,
        roller_name=req_data.roller_name,
        formula=req_data.formula,
        roll=result,
    )
    await repo.save(session)

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
