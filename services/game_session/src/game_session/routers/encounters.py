"""Encounter start route: one owner write that starts combat and places enemy tokens (TASK-0749).

game_session records the combat start and the placements on one event. That save is the commit
point, and the route answers 200 after it. board_state consumes the event and places the tokens.
A placement that fails later leaves the combat started. The route never undoes it.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from game_session.encounter_settings import EncounterGridSettings
from game_session.models import CombatStateResponse
from game_session.play.repositories import SessionRepo
from game_session.routers.combat import _build_combat_response
from game_session.routers.session_auth import session_permission
from pydantic import BaseModel, Field
from runefoble_platform.aggregate_loading import load_if_exists

router = APIRouter(tags=["encounters"])


class EncounterEnemy(BaseModel):
    """One enemy that the encounter starts with and places on the board."""

    name: str = Field(min_length=1)
    x: int
    y: int
    hp: int | None = Field(default=None, ge=0)
    cr: float = Field(ge=0)


class StartEncounterResponse(CombatStateResponse):
    """The combat state after the start, and the enemy placements that the start recorded."""

    placements: list[dict[str, object]] = Field(default_factory=list)


class StartEncounterRequest(BaseModel):
    """The enemies of a new encounter. The gateway reads each challenge rating first."""

    enemies: list[EncounterEnemy] = Field(default_factory=list)


def _combatants(enemies: list[EncounterEnemy]) -> list[dict[str, object]]:
    return [
        {
            "combatant_id": f"enemy-{index}",
            "name": enemy.name,
            "hp": enemy.hp,
            "is_npc": True,
            "cr": enemy.cr,
        }
        for index, enemy in enumerate(enemies, start=1)
    ]


def _placements(enemies: list[EncounterEnemy]) -> list[dict[str, object]]:
    return [
        {
            "name": enemy.name,
            "token_type": "monster",
            "x": enemy.x,
            "y": enemy.y,
            "hp": enemy.hp,
            "is_friendly": False,
        }
        for enemy in enemies
    ]


@router.post(
    "/api/v1/sessions/{session_id}/encounters/start",
    response_model=StartEncounterResponse,
)
async def start_encounter(
    session_id: UUID,
    req: StartEncounterRequest,
    repo: SessionRepo,
    actor: str = Depends(session_permission("control")),
) -> StartEncounterResponse:
    """Start combat and record the enemy placements on one event. Answer 200 after that save."""
    session = await load_if_exists(repo, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")
    grid = EncounterGridSettings()
    placements = _placements(req.enemies)
    try:
        session.start_combat(
            combatants=_combatants(req.enemies),
            board_cols=grid.cols,
            board_rows=grid.rows,
            placements=placements,
            initiated_by=actor,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    await repo.save(session)
    combat = _build_combat_response(session)
    return StartEncounterResponse(**combat.model_dump(), placements=placements)
