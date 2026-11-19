"""Encounter start route: one owner write that starts combat and places enemy tokens (TASK-0749).

game_session records the combat start and the placements on one event. That save is the commit
point, and the route answers 200 after it. board_state consumes the event and places the tokens.
A placement that fails later leaves the combat started. The route never undoes it.

game_session resolves each challenge rating before the start (TASK-0918). An enemy without `cr`
gets the rating of its rules_compendium stat block. An enemy with no rating in either place
gives 400, and a compendium failure gives 503. Both start no combat.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException
from game_session.compendium_client import CompendiumUnavailableError, fetch_challenge_ratings
from game_session.encounter_settings import EncounterGridSettings
from game_session.models import CombatStateResponse
from game_session.play.repositories import SessionRepo
from game_session.routers.combat import _build_combat_response
from game_session.routers.session_auth import session_permission
from pydantic import BaseModel, Field
from runefoble_platform.aggregate_loading import load_if_exists

router = APIRouter(tags=["encounters"])


class EncounterEnemy(BaseModel):
    """One enemy that the encounter starts with and places on the board.

    `cr` is the challenge rating. When it is absent, rules_compendium supplies it by `name`.
    """

    name: str = Field(min_length=1)
    x: int
    y: int
    hp: int | None = Field(default=None, ge=0)
    cr: float | None = Field(default=None, ge=0)


class StartEncounterResponse(CombatStateResponse):
    """The combat state after the start, and the enemy placements that the start recorded."""

    placements: list[dict[str, object]] = Field(default_factory=list)


class StartEncounterRequest(BaseModel):
    """The enemies of a new encounter.

    `campaign_id` names the campaign whose homebrew monsters resolve by name.
    """

    campaign_id: UUID | None = None
    enemies: list[EncounterEnemy] = Field(default_factory=list)


async def _resolve_ratings(req: StartEncounterRequest, authorization: str | None) -> list[float]:
    """Return the challenge rating of each enemy, in order. Read the missing ones concurrently.

    Raise HTTPException 400 when an enemy has no rating, and 503 when rules_compendium fails.
    A missing rating is never scored as zero.
    """
    missing = [enemy.name for enemy in req.enemies if enemy.cr is None]
    try:
        looked_up = iter(
            await fetch_challenge_ratings(
                missing, campaign_id=req.campaign_id, authorization=authorization
            )
        )
    except CompendiumUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    ratings = [enemy.cr if enemy.cr is not None else next(looked_up) for enemy in req.enemies]
    unrated = [
        enemy.name for enemy, rating in zip(req.enemies, ratings, strict=True) if rating is None
    ]
    if unrated:
        subject = ", ".join(f"'{name}'" for name in unrated)
        subject = f"Enemy {subject} has" if len(unrated) == 1 else f"Enemies {subject} have"
        raise HTTPException(
            status_code=400,
            detail=(
                f"{subject} no challenge rating. Give cr in the request "
                "or use a monster name from the compendium."
            ),
        )
    return [rating for rating in ratings if rating is not None]


def _combatants(enemies: list[EncounterEnemy], ratings: list[float]) -> list[dict[str, object]]:
    return [
        {
            "combatant_id": f"enemy-{index}",
            "name": enemy.name,
            "hp": enemy.hp,
            "is_npc": True,
            "cr": rating,
        }
        for index, (enemy, rating) in enumerate(zip(enemies, ratings, strict=True), start=1)
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
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
) -> StartEncounterResponse:
    """Start combat and record the enemy placements on one event. Answer 200 after that save."""
    session = await load_if_exists(repo, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")
    ratings = await _resolve_ratings(req, authorization)
    grid = EncounterGridSettings()
    placements = _placements(req.enemies)
    try:
        session.start_combat(
            combatants=_combatants(req.enemies, ratings),
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
