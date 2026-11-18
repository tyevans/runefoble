"""DM override and atmosphere routes for a live game session (TASK-0581).

Each route loads the session aggregate, records one event, and saves through the repository.
"""

from __future__ import annotations

from uuid import UUID

from eventsource.domain.exceptions import AggregateNotFoundError
from fastapi import APIRouter, Depends, HTTPException
from game_session.aggregate import GameSessionAggregate
from game_session.dependencies import repo
from game_session.models import AtmosphereUpdateRequest, DMOverrideRequest, GameSessionState
from game_session.settlement.auth.tokens import get_caller_principal

router = APIRouter(dependencies=[Depends(get_caller_principal)], tags=["session"])


async def _load_session(session_id: UUID) -> GameSessionAggregate:
    try:
        return await repo.load(session_id)
    except AggregateNotFoundError as e:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}") from e


@router.post("/api/v1/sessions/{session_id}/dm-override", response_model=GameSessionState)
async def apply_dm_override(session_id: UUID, req: DMOverrideRequest) -> GameSessionState:
    """Record a DM override on the session. The override appears in the session state."""
    session = await _load_session(session_id)
    try:
        session.apply_dm_override(action=req.action, reason=req.reason, payload=req.payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    await repo.save(session)
    return session.state


@router.post("/api/v1/sessions/{session_id}/atmosphere", response_model=GameSessionState)
async def update_atmosphere(session_id: UUID, req: AtmosphereUpdateRequest) -> GameSessionState:
    """Change the location, lighting, and mood of the session."""
    session = await _load_session(session_id)
    try:
        session.update_atmosphere(
            location_name=req.location_name,
            lighting=req.lighting,
            mood=req.mood,
            description=req.description,
            ambient_audio_prompt=req.ambient_audio_prompt,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    await repo.save(session)
    return session.state
