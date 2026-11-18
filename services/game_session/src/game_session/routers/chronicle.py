"""Read routes for the session chronicle feed and the absentee recap (TASK-0641).

Both routes verify the caller's token through `get_caller_or_service`, as the session read does.
The gateway applies the `observe` check before it proxies here. An unknown session returns 404.
"""

from __future__ import annotations

from uuid import UUID

from eventsource.domain.exceptions import AggregateNotFoundError
from fastapi import APIRouter, Depends, HTTPException
from game_session.aggregate import GameSessionAggregate
from game_session.chronicle import (
    AbsenteeRecap,
    ChronicleEntry,
    build_absentee_recap,
    read_session_chronicle,
)
from game_session.dependencies import repo
from game_session.settlement.auth.tokens import get_caller_or_service

router = APIRouter(tags=["session"])


async def _require_session(session_id: UUID) -> GameSessionAggregate:
    """Load the session or raise 404 when no session has that id."""
    try:
        return await repo.load(session_id)
    except AggregateNotFoundError as e:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}") from e


@router.get(
    "/api/v1/sessions/{session_id}/events",
    dependencies=[Depends(get_caller_or_service)],
    response_model=list[ChronicleEntry],
)
async def list_session_events(session_id: UUID) -> list[ChronicleEntry]:
    """Return the chronicle feed lines of a session in commit order. An empty session returns []."""
    await _require_session(session_id)
    return await read_session_chronicle(session_id)


@router.get(
    "/api/v1/sessions/{session_id}/absentee-recap",
    dependencies=[Depends(get_caller_or_service)],
    response_model=AbsenteeRecap,
)
async def get_absentee_recap(session_id: UUID) -> AbsenteeRecap:
    """Return the stand-in turns and penalties that the session recorded. No turns returns an empty recap."""
    session = await _require_session(session_id)
    return build_absentee_recap(session.state)
