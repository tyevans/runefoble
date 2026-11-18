"""Combat encounter and initiative order routes for Game Session service."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from game_session.aggregate import GameSessionAggregate
from game_session.dependencies import repo as default_repo
from game_session.models import (
    CombatStateResponse,
    InitiativeRollRequest,
    NextTurnRequest,
    StartCombatRequest,
)
from game_session.routers.session_auth import SessionReader, session_permission
from runefoble_platform.event_sourcing import AggregateRepository

router = APIRouter(tags=["combat"])

_repo: AggregateRepository[GameSessionAggregate] = default_repo


def _build_combat_response(
    session: GameSessionAggregate, turn_seconds: int = 60
) -> CombatStateResponse:
    return CombatStateResponse(
        session_id=session.aggregate_id,
        in_combat=session.state.in_combat,
        combat_round=session.state.combat_round,
        combat_active_id=session.state.combat_active_id,
        initiative_order=session.state.initiative_order,
        turn_seconds_remaining=turn_seconds,
    )


@router.post(
    "/api/v1/sessions/{session_id}/combat/start",
    dependencies=[Depends(session_permission("control"))],
    response_model=CombatStateResponse,
)
async def start_combat_encounter(session_id: UUID, req: StartCombatRequest | None = None):
    """Start combat encounter and initiate turn/round tracking."""
    combatants = req.combatants if req else []
    try:
        session = await _repo.load(session_id)
        session.start_combat(combatants=combatants)
        await _repo.save(session)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Session not found: {e}") from e

    return _build_combat_response(session)


@router.post(
    "/api/v1/sessions/{session_id}/combat/initiative",
    dependencies=[Depends(session_permission("control"))],
    response_model=CombatStateResponse,
)
async def roll_combat_initiative(session_id: UUID, req: InitiativeRollRequest):
    """Submit or update initiative roll for a combatant."""
    try:
        session = await _repo.load(session_id)
        session.roll_initiative(
            combatant_id=req.combatant_id,
            combatant_name=req.combatant_name,
            initiative_score=req.initiative_score,
            is_npc=req.is_npc,
        )
        await _repo.save(session)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Session not found: {e}") from e

    return _build_combat_response(session)


@router.post(
    "/api/v1/sessions/{session_id}/combat/next-turn",
    dependencies=[Depends(session_permission("control"))],
    response_model=CombatStateResponse,
)
async def advance_combat_turn(session_id: UUID, req: NextTurnRequest | None = None):
    """Advance turn to next combatant in initiative order, cycling rounds."""
    turn_secs = req.turn_seconds if req else 60
    try:
        session = await _repo.load(session_id)
        session.advance_initiative(turn_seconds_remaining=turn_secs)
        await _repo.save(session)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Session not found: {e}") from e

    return _build_combat_response(session, turn_seconds=turn_secs)


@router.post(
    "/api/v1/sessions/{session_id}/combat/end",
    dependencies=[Depends(session_permission("control"))],
    response_model=CombatStateResponse,
)
async def end_combat_encounter(session_id: UUID):
    """Conclude active combat encounter."""
    try:
        session = await _repo.load(session_id)
        session.end_combat()
        await _repo.save(session)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Session not found: {e}") from e

    return _build_combat_response(session)


@router.get(
    "/api/v1/sessions/{session_id}/combat",
    dependencies=[SessionReader],
    response_model=CombatStateResponse,
)
async def get_combat_state(session_id: UUID):
    """Retrieve current combat encounter state, initiative order, active turn, and timer."""
    try:
        session = await _repo.load(session_id)
        return _build_combat_response(session)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Session not found: {e}") from e
