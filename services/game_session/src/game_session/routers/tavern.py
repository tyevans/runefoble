"""FastAPI APIRouter for tavern minigames and merchant haggling.

Part of TASK-0103 / PRD-0014 / US-0047.
Governed by Hard Invariant 1 (SpiceDB auth) and Hard Invariant 2 (eventsource-py aggregates).
"""

from __future__ import annotations

import contextlib
from typing import Any, Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Header, HTTPException
from game_session.dependencies import (
    STREAM_TAVERN,
    get_event_bus,
    get_merchant_repository,
    get_spicedb_client,
    get_tavern_repository,
)
from game_session.dependencies import (
    repo as session_repo,
)
from game_session.merchants import MERCHANT_TEMPERAMENTS, MerchantAggregate
from game_session.minigames import (
    TavernGameAggregate,
    TavernGameState,
    to_uuid,
)
from pydantic import BaseModel

router = APIRouter(tags=["tavern"])


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


async def _check_session_auth(session_id: str, user_id: str | None) -> None:
    if not user_id:
        return
    spicedb = get_spicedb_client()
    has_perm = await spicedb.check_permission(
        "session", str(session_id), "participate", "user", user_id
    )
    if not has_perm:
        # Fallback to campaign permission if session not explicitly mapped
        try:
            sess = await session_repo.load(
                UUID(session_id) if len(session_id) == 36 else session_id
            )
            if sess.state.campaign_id:
                has_perm = await spicedb.check_permission(
                    "campaign", str(sess.state.campaign_id), "play", "user", user_id
                )
        except Exception:
            pass
    if not has_perm:
        raise HTTPException(status_code=403, detail="Player or DM permission required")


@router.post("/api/v1/sessions/{session_id}/tavern/games", response_model=TavernGameState)
async def start_minigame(
    session_id: str,
    req: StartMinigameRequest,
    x_user_id: str | None = Header(default=None),
) -> TavernGameState:
    """Start an interactive tavern minigame with wager."""
    await _check_session_auth(session_id, x_user_id)
    game_id = f"game-{uuid4().hex[:8]}"

    tavern_repo = get_tavern_repository()
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

    bus = get_event_bus()
    if bus:
        for ev in events_to_publish:
            with contextlib.suppress(Exception):
                await bus.publish_event(STREAM_TAVERN, ev)

    return aggregate.state


@router.post(
    "/api/v1/sessions/{session_id}/tavern/games/{game_id}/turn",
    response_model=dict[str, Any],
)
async def take_minigame_turn(
    session_id: str,
    game_id: str,
    req: MinigameTurnRequest,
    x_user_id: str | None = Header(default=None),
) -> dict[str, Any]:
    """Submit a turn or wager action in an active tavern minigame."""
    await _check_session_auth(session_id, x_user_id)
    tavern_repo = get_tavern_repository()

    try:
        aggregate = await tavern_repo.load(to_uuid(game_id))
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Minigame '{game_id}' not found") from e

    try:
        if req.action_type == "bid":
            if req.quantity is None or req.face is None:
                raise ValueError("Quantity and face value are required for bid")
            turn_result = aggregate.submit_bid(req.actor_id, req.quantity, req.face)
        elif req.action_type == "challenge":
            turn_result = aggregate.call_challenge(req.actor_id)
        elif req.action_type == "drink":
            turn_result = aggregate.take_drink(
                req.actor_id, con_roll=req.con_roll, speech_text=req.speech_text
            )
        else:
            raise ValueError(f"Action '{req.action_type}' not supported")

        events_to_publish = list(aggregate.uncommitted_events)
        await tavern_repo.save(aggregate)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    bus = get_event_bus()
    if bus:
        for ev in events_to_publish:
            with contextlib.suppress(Exception):
                await bus.publish_event(STREAM_TAVERN, ev)

    return {
        "game_id": game_id,
        "action_type": req.action_type,
        "actor_id": req.actor_id,
        "result": turn_result,
        "state": aggregate.state.model_dump(),
    }


@router.get("/api/v1/sessions/{session_id}/tavern/games/{game_id}", response_model=TavernGameState)
async def get_minigame(
    session_id: str,
    game_id: str,
    x_user_id: str | None = Header(default=None),
) -> TavernGameState:
    """Get active status and state machine details for a minigame."""
    await _check_session_auth(session_id, x_user_id)
    tavern_repo = get_tavern_repository()
    try:
        aggregate = await tavern_repo.load(to_uuid(game_id))
        return aggregate.state
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Minigame '{game_id}' not found") from e


@router.post(
    "/api/v1/sessions/{session_id}/merchants/{merchant_id}/haggle",
    response_model=HaggleResponse,
)
async def haggle_merchant(
    session_id: str,
    merchant_id: str,
    req: HaggleRequest,
    temperament: str = "stubborn_greedy",
    x_user_id: str | None = Header(default=None),
) -> HaggleResponse:
    """Negotiate with an NPC merchant influenced by dynamic temperament and mood."""
    await _check_session_auth(session_id, x_user_id)
    merchant_repo = get_merchant_repository()

    try:
        aggregate = await merchant_repo.load(to_uuid(merchant_id))
    except Exception:
        aggregate = MerchantAggregate(to_uuid(merchant_id))
        aggregate.state.merchant_id = merchant_id
        if temperament in MERCHANT_TEMPERAMENTS:
            aggregate.state.temperament = temperament
            aggregate.state.name = MERCHANT_TEMPERAMENTS[temperament]["default_name"]

    res = aggregate.negotiate(
        character_id=req.character_id,
        item_name=req.item_name,
        base_price=req.base_price,
        offered_price=req.offered_price,
        charisma_modifier=req.charisma_modifier,
        dialogue=req.dialogue,
        session_id=session_id,
    )

    events_to_publish = list(aggregate.uncommitted_events)
    await merchant_repo.save(aggregate)

    bus = get_event_bus()
    if bus:
        for ev in events_to_publish:
            with contextlib.suppress(Exception):
                await bus.publish_event(STREAM_TAVERN, ev)

    return HaggleResponse(
        merchant_id=merchant_id,
        temperament=res["temperament"],
        outcome=res["outcome"],
        base_price=res["base_price"],
        offered_price=res["offered_price"],
        counter_price=res["counter_price"],
        agreed_price=res["agreed_price"],
        mood_score=res["mood_score"],
        voice_bark=res["voice_bark"],
    )


@router.get("/api/v1/merchants/{merchant_id}")
async def get_merchant(merchant_id: str) -> dict[str, Any]:
    """Retrieve merchant temperament, mood score, and bartering history."""
    merchant_repo = get_merchant_repository()
    try:
        aggregate = await merchant_repo.load(to_uuid(merchant_id))
        data = aggregate.state.model_dump()
        data["merchant_id"] = merchant_id
        return data
    except Exception:
        return {
            "merchant_id": merchant_id,
            "name": "Local Merchant",
            "temperament": "shrewd",
            "mood_score": 0.0,
            "total_negotiations": 0,
        }


__all__ = ["router"]
