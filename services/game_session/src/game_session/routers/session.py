"""Session lifecycle, participation, lobby readiness, turns, and dice roll routes.

Every route saves through the session aggregate. The session repository publishes the
committed events to their streams, so routes do not publish directly.
"""

from __future__ import annotations

from collections.abc import Awaitable
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Header, HTTPException
from game_session.aggregate import GameSessionAggregate, GameSessionState
from game_session.campaign.tuples import link_session
from game_session.character_client import (
    CharacterSheetUnavailableError,
    activate_stand_in,
    release_stand_in,
)
from game_session.dependencies import repo
from game_session.models import (
    CreateSessionRequest,
    HotSwapRequest,
    HotSwapResponse,
    JoinSessionRequest,
    LeaveSessionRequest,
    LeaveSessionResponse,
    ReadinessRequest,
    RollDiceRequest,
    RollDiceResponse,
    SelectLobbyCharacterRequest,
)
from game_session.routers.session_auth import (
    SessionController,
    SessionParticipant,
    SessionReader,
)
from game_session.settlement.auth.tokens import (
    CallerId,
)
from runefoble_auth.factory import get_spicedb_client
from runefoble_platform.aggregate_loading import load_or_404
from runefoble_platform.dice import parse_and_roll

router = APIRouter(tags=["session"])


async def _load_session(session_id: UUID) -> GameSessionAggregate:
    """Load a session by id. Raise 404 when no session has that id."""
    return await load_or_404(repo, session_id, f"Session not found: {session_id}")


@router.post(
    "/api/v1/sessions/create",
    response_model=GameSessionState,
)
async def create_session(req: CreateSessionRequest, caller_id: CallerId) -> GameSessionState:
    """Create a new event-sourced game session in a campaign the caller can run.

    The caller needs `run_session` on the campaign. The check runs before the session is saved
    and before the campaign link is written, so a refused caller leaves no state behind.
    """
    spicedb = get_spicedb_client()
    allowed = await spicedb.check_permission(
        resource_type="campaign",
        resource_id=str(req.campaign_id),
        permission="run_session",
        subject_type="user",
        subject_id=caller_id,
    )
    if not allowed:
        raise HTTPException(
            status_code=403,
            detail=f"User '{caller_id}' lacks 'run_session' on campaign '{req.campaign_id}'",
        )
    session_id = uuid4()
    session = GameSessionAggregate(session_id)
    session.create(campaign_id=req.campaign_id, title=req.title, dm_id=req.dm_id)
    await repo.save(session)
    # Link after the save (ADR-0001). The gateway's observe and control checks read this link.
    await link_session(spicedb, str(session_id), str(req.campaign_id))
    return session.state


@router.get(
    "/api/v1/sessions/{session_id}",
    dependencies=[SessionReader],
    response_model=GameSessionState,
)
async def get_session(session_id: UUID) -> GameSessionState:
    """Load session state reconstituted from the event stream."""
    try:
        session = await repo.load(session_id)
        return session.state
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Session not found: {e}") from e


@router.post("/api/v1/sessions/{session_id}/start", response_model=GameSessionState)
async def start_session(session_id: UUID, _controller: SessionController) -> GameSessionState:
    """Transition session from lobby to active. The caller needs `session.control`."""
    session = await _load_session(session_id)
    try:
        session.start()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    await repo.save(session)
    return session.state


@router.post("/api/v1/sessions/{session_id}/join", response_model=GameSessionState)
async def join_session(
    session_id: UUID,
    req: JoinSessionRequest,
    player_id: SessionParticipant,
    authorization: Annotated[str, Header(alias="Authorization")],
) -> GameSessionState:
    """Seat the verified caller. A returning absent player releases the stand-in."""
    session = await _load_session(session_id)
    stand_in_character_id = _active_stand_in_character(session.state, player_id)
    try:
        session.join_player(
            player_id=player_id,
            character_id=req.character_id,
            character_name=req.character_name,
            character_class=req.character_class,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    if stand_in_character_id is not None:
        await _call_character_sheet(
            release_stand_in(stand_in_character_id, session_id, authorization=authorization)
        )
    await repo.save(session)
    return session.state


@router.post("/api/v1/sessions/{session_id}/leave", response_model=LeaveSessionResponse)
async def leave_session(
    session_id: UUID,
    req: LeaveSessionRequest,
    player_id: SessionParticipant,
    authorization: Annotated[str, Header(alias="Authorization")],
) -> LeaveSessionResponse:
    """Record the verified caller's absence. The lobby character goes to the AI stand-in (TASK-0690).

    character_sheet owns the stand-in flag. The leave is saved only after it accepts the
    activation. A player with no lobby character records the absence only.
    """
    session = await _load_session(session_id)
    try:
        session.leave_player(player_id=player_id, reason=req.reason)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    character_id = session.state.lobby_characters.get(player_id)
    if character_id is not None:
        await _call_character_sheet(
            activate_stand_in(character_id, session_id, authorization=authorization)
        )
    await repo.save(session)
    return LeaveSessionResponse(**session.state.model_dump(), stand_in_character_id=character_id)


def _active_stand_in_character(state: GameSessionState, player_id: str) -> UUID | None:
    """Return the character that holds the stand-in for an absent player, if any."""
    participant = state.participants.get(player_id)
    if participant is None or not participant.is_stand_in_active:
        return None
    return state.lobby_characters.get(player_id)


async def _call_character_sheet(call: Awaitable[None]) -> None:
    """Await a character_sheet call. Map an upstream failure to 503, never to a fake success."""
    try:
        await call
    except CharacterSheetUnavailableError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e


@router.post("/api/v1/sessions/{session_id}/lobby/readiness", response_model=GameSessionState)
async def toggle_lobby_readiness(
    session_id: UUID, req: ReadinessRequest, player_id: SessionParticipant
) -> GameSessionState:
    """Record the verified caller's readiness in the session lobby."""
    session = await _load_session(session_id)
    try:
        session.toggle_readiness(player_id=player_id, is_ready=req.is_ready)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    await repo.save(session)
    return session.state


@router.post("/api/v1/sessions/{session_id}/lobby/character", response_model=GameSessionState)
async def select_lobby_character(
    session_id: UUID, req: SelectLobbyCharacterRequest, player_id: SessionParticipant
) -> GameSessionState:
    """Record which character the verified caller brings to the session lobby."""
    session = await _load_session(session_id)
    try:
        session.select_lobby_character(player_id=player_id, character_id=req.character_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    await repo.save(session)
    return session.state


@router.post("/api/v1/sessions/{session_id}/hot-swap", response_model=HotSwapResponse)
async def hot_swap_session(
    player_id: SessionParticipant,
    session_id: UUID,
    req: HotSwapRequest,
    authorization: Annotated[str, Header(alias="Authorization")],
) -> HotSwapResponse:
    """Hand active turn control from the AI stand-in to the verified caller mid-session.

    The caller needs `session.participate` and `character.edit` on the character taken over.
    """
    allowed = await get_spicedb_client().check_permission(
        resource_type="character",
        resource_id=str(req.character_id),
        permission="edit",
        subject_type="user",
        subject_id=player_id,
    )
    if not allowed:
        raise HTTPException(
            status_code=403,
            detail=f"User '{player_id}' does not have permission to take control of character '{req.character_id}'",
        )

    session = await _load_session(session_id)
    try:
        session.hot_swap_character(player_id=player_id, character_id=req.character_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    try:
        await release_stand_in(req.character_id, session_id, authorization=authorization)
    except CharacterSheetUnavailableError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    await repo.save(session)

    return HotSwapResponse(
        session_id=session_id,
        character_id=req.character_id,
        player_id=player_id,
        previous_controller="ai_stand_in",
        new_controller="player",
        current_turn=session.state.current_turn,
        in_combat=session.state.in_combat,
        combat_round=session.state.combat_round,
        combat_active_id=session.state.combat_active_id,
        session_state=session.state,
    )


@router.post(
    "/api/v1/sessions/{session_id}/next-turn",
    response_model=GameSessionState,
)
async def advance_turn(session_id: UUID, _controller: SessionController) -> GameSessionState:
    """Advance to the next turn in the session."""
    session = await _load_session(session_id)
    try:
        session.advance_turn()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    await repo.save(session)
    return session.state


@router.post(
    "/api/v1/sessions/{session_id}/roll",
    response_model=RollDiceResponse,
)
async def roll_dice_session(
    session_id: UUID, roller_id: SessionParticipant, req: RollDiceRequest | None = None
) -> RollDiceResponse:
    """Evaluate a dice roll for the verified caller and record it on the session aggregate."""
    req_data = req or RollDiceRequest()
    session = await _load_session(session_id)
    try:
        result = parse_and_roll(req_data.formula)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    session.record_dice_roll(
        roller_id=roller_id,
        roller_name=req_data.roller_name,
        formula=req_data.formula,
        roll=result,
    )
    await repo.save(session)

    return RollDiceResponse(
        session_id=session_id,
        roller_id=roller_id,
        roller_name=req_data.roller_name,
        formula=req_data.formula,
        total=result["total"],
        rolls=result["rolls"],
        is_crit=result.get("is_crit", False),
        is_fumble=result.get("is_fumble", False),
        roll_type=req_data.roll_type,
    )
