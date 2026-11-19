"""FastAPI APIRouter for tavern minigames and merchant haggling.

Part of TASK-0103 / PRD-0014 / US-0047.
Governed by Hard Invariant 1 (SpiceDB auth) and Hard Invariant 2 (eventsource-py aggregates).
"""

from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException
from game_session.auth import check_session_participation
from game_session.downtime.repositories import DowntimeRepos
from game_session.merchants_service import HaggleOffer, haggle, load_merchant_profile
from game_session.minigame_tables.models import MinigameTableState
from game_session.minigame_tables.service import (
    TableAlreadyOpenError,
    TableNotFoundError,
    load_table,
    open_table,
)
from game_session.minigames import (
    TavernGameAggregate,
    TavernGameState,
)
from game_session.play.repositories import SessionRepo
from game_session.shared.container_access import EventBus
from game_session.shared.identity import CallerId, get_principal
from game_session.shared.permissions import check_establishment_play_permission
from game_session.shared.streams import STREAM_TAVERN
from game_session.voice_client import VoiceAgentUnavailableError
from pydantic import BaseModel
from runefoble_auth.factory import get_spicedb_client
from runefoble_platform.aggregate_loading import load_if_exists
from runefoble_platform.event_publish import publish_aggregate_events
from runefoble_platform.identifiers import opaque_aggregate_id

router = APIRouter(dependencies=[Depends(get_principal)], tags=["tavern"])


class StartMinigameRequest(BaseModel):
    game_type: Literal["liars_dice", "card_duel", "drinking_contest"] = "liars_dice"
    wager_gold: int = 10
    initiator_id: str
    challenger_id: str = "npc_pirate"


class MinigameTurnRequest(BaseModel):
    actor_id: str
    action_type: Literal["bid", "challenge", "play_card", "drink", "pass"]
    quantity: int | None = None
    face: int | None = None
    con_roll: int | None = None
    speech_text: str | None = None


class HaggleRequest(BaseModel):
    character_id: str
    item_name: str
    base_price: int
    offered_price: int
    charisma_modifier: int = 0
    dialogue: str = ""


class HaggleResponse(BaseModel):
    merchant_id: str
    temperament: str
    outcome: str
    base_price: int
    offered_price: int
    counter_price: int | None = None
    agreed_price: int | None = None
    mood_score: float
    voice_bark: str | None = None


class OpenTableRequest(BaseModel):
    table_id: str
    establishment_id: str
    game_type: Literal["darts", "liars_dice", "roulette", "craps", "billiards"] = "darts"


async def _require_table_play(establishment_id: str, user_id: str) -> None:
    has_perm = await check_establishment_play_permission(
        get_spicedb_client(), establishment_id, user_id
    )
    if not has_perm:
        raise HTTPException(
            status_code=403, detail="Play permission required at this establishment"
        )


@router.post("/api/v1/tavern/tables", response_model=MinigameTableState, status_code=201)
async def open_minigame_table(
    caller_id: CallerId, req: OpenTableRequest, repos: DowntimeRepos, events: EventBus
) -> MinigameTableState:
    """Open a minigame table. Sockets join only tables opened here (TASK-0566)."""
    await _require_table_play(req.establishment_id, caller_id)
    try:
        return await open_table(
            repos.tavern_games, events, req.table_id, req.establishment_id, req.game_type
        )
    except TableAlreadyOpenError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/api/v1/tavern/tables/{table_id}", response_model=MinigameTableState)
async def get_minigame_table(
    caller_id: CallerId, table_id: str, repos: DowntimeRepos
) -> MinigameTableState:
    """Read the seats, chips, pot, and game state of an open minigame table."""
    try:
        table = await load_table(repos.tavern_games, table_id)
    except TableNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    await _require_table_play(table.establishment_id, caller_id)
    return table


@router.post("/api/v1/sessions/{session_id}/tavern/games", response_model=TavernGameState)
async def start_minigame(
    caller_id: CallerId,
    session_id: str,
    req: StartMinigameRequest,
    sessions: SessionRepo,
    repos: DowntimeRepos,
    events: EventBus,
) -> TavernGameState:
    """Start an interactive tavern minigame with wager."""
    await check_session_participation(sessions, session_id, caller_id)
    game_id = f"game-{uuid4().hex[:8]}"

    tavern_repo = repos.tavern_games
    aggregate = TavernGameAggregate(game_id)
    aggregate.start_game(
        game_id=game_id,
        game_type=req.game_type,
        wager_gold=req.wager_gold,
        initiator_id=req.initiator_id,
        challenger_id=req.challenger_id,
        session_id=session_id,
    )

    events_to_publish = list(aggregate.uncommitted_events)
    await tavern_repo.save(aggregate)

    bus = events.get()
    if bus:
        await publish_aggregate_events(bus, STREAM_TAVERN, events_to_publish)

    return aggregate.state


@router.post(
    "/api/v1/sessions/{session_id}/tavern/games/{game_id}/turn",
    response_model=dict[str, Any],
)
async def take_minigame_turn(
    caller_id: CallerId,
    session_id: str,
    game_id: str,
    req: MinigameTurnRequest,
    sessions: SessionRepo,
    repos: DowntimeRepos,
    events: EventBus,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    """Submit a turn or wager action in an active tavern minigame."""
    await check_session_participation(sessions, session_id, caller_id)
    tavern_repo = repos.tavern_games

    aggregate = await load_if_exists(tavern_repo, opaque_aggregate_id(game_id, field="game_id"))
    if aggregate is None:
        raise HTTPException(status_code=404, detail=f"Minigame '{game_id}' not found")

    try:
        if req.action_type == "bid":
            if req.quantity is None or req.face is None:
                raise ValueError("Quantity and face value are required for bid")
            turn_result = aggregate.submit_bid(req.actor_id, req.quantity, req.face)
        elif req.action_type == "challenge":
            turn_result = aggregate.call_challenge(req.actor_id)
        elif req.action_type == "drink":
            turn_result = await aggregate.take_drink(
                req.actor_id,
                con_roll=req.con_roll,
                speech_text=req.speech_text,
                authorization=authorization,
            )
        else:
            raise ValueError(f"Action '{req.action_type}' not supported")

        events_to_publish = list(aggregate.uncommitted_events)
        await tavern_repo.save(aggregate)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except VoiceAgentUnavailableError as e:
        raise HTTPException(status_code=503, detail=f"Voice DSP unavailable: {e}") from e

    bus = events.get()
    if bus:
        await publish_aggregate_events(bus, STREAM_TAVERN, events_to_publish)

    return {
        "game_id": game_id,
        "action_type": req.action_type,
        "actor_id": req.actor_id,
        "result": turn_result,
        "state": aggregate.state.model_dump(),
    }


@router.get("/api/v1/sessions/{session_id}/tavern/games/{game_id}", response_model=TavernGameState)
async def get_minigame(
    caller_id: CallerId,
    session_id: str,
    game_id: str,
    sessions: SessionRepo,
    repos: DowntimeRepos,
) -> TavernGameState:
    """Get active status and state machine details for a minigame."""
    await check_session_participation(sessions, session_id, caller_id)
    aggregate = await load_if_exists(
        repos.tavern_games, opaque_aggregate_id(game_id, field="game_id")
    )
    if aggregate is None:
        raise HTTPException(status_code=404, detail=f"Minigame '{game_id}' not found")
    return aggregate.state


@router.post(
    "/api/v1/sessions/{session_id}/merchants/{merchant_id}/haggle",
    response_model=HaggleResponse,
)
async def haggle_merchant(
    caller_id: CallerId,
    session_id: str,
    merchant_id: str,
    req: HaggleRequest,
    sessions: SessionRepo,
    repos: DowntimeRepos,
    events: EventBus,
    temperament: str = "stubborn_greedy",
) -> HaggleResponse:
    """Negotiate with an NPC merchant influenced by dynamic temperament and mood."""
    await check_session_participation(sessions, session_id, caller_id)
    result = await haggle(
        repos.merchants,
        events,
        merchant_id=merchant_id,
        session_id=session_id,
        temperament=temperament,
        offer=HaggleOffer(
            character_id=req.character_id,
            item_name=req.item_name,
            base_price=req.base_price,
            offered_price=req.offered_price,
            charisma_modifier=req.charisma_modifier,
            dialogue=req.dialogue,
        ),
    )

    return HaggleResponse(
        merchant_id=merchant_id,
        temperament=result.temperament,
        outcome=result.outcome,
        base_price=result.base_price,
        offered_price=result.offered_price,
        counter_price=result.counter_price,
        agreed_price=result.agreed_price,
        mood_score=result.mood_score,
        voice_bark=result.voice_bark,
    )


@router.get("/api/v1/merchants/{merchant_id}")
async def get_merchant(merchant_id: str, repos: DowntimeRepos) -> dict[str, Any]:
    """Retrieve merchant temperament, mood score, and bartering history."""
    profile = await load_merchant_profile(repos.merchants, merchant_id)
    if profile is None:
        raise HTTPException(status_code=404, detail=f"Merchant '{merchant_id}' not found")
    return profile


__all__ = ["router"]
