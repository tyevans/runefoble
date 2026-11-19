"""Read routes for the session chronicle feed and the absentee recap (TASK-0641).

Both routes verify the caller's token and require `session.observe` for a user caller (ADR-0001),
as the session read does. An unknown session returns 404 after the permission check.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from game_session.aggregate import GameSessionAggregate
from game_session.chronicle import (
    AbsenteeRecap,
    ChronicleEntry,
    build_absentee_recap,
    read_session_chronicle,
)
from game_session.dependencies import repo
from game_session.routers.session_auth import session_reader
from game_session.settlement.auth.tokens import CallerOrService
from runefoble_platform.aggregate_loading import load_or_404

router = APIRouter(tags=["session"])


async def _observer_of_existing_session(session_id: UUID, caller: CallerOrService) -> None:
    """Return 404 for an unknown session, then require `session.observe` for a user caller."""
    await _require_session(session_id)
    await session_reader(session_id, caller)


async def _require_session(session_id: UUID) -> GameSessionAggregate:
    """Load the session or raise 404 when no session has that id."""
    return await load_or_404(repo, session_id, f"Session not found: {session_id}")


@router.get(
    "/api/v1/sessions/{session_id}/events",
    dependencies=[Depends(_observer_of_existing_session)],
    response_model=list[ChronicleEntry],
)
async def list_session_events(session_id: UUID) -> list[ChronicleEntry]:
    """Return the chronicle feed lines of a session in commit order. An empty session returns []."""
    await _require_session(session_id)
    return await read_session_chronicle(session_id)


@router.get(
    "/api/v1/sessions/{session_id}/absentee-recap",
    dependencies=[Depends(_observer_of_existing_session)],
    response_model=AbsenteeRecap,
)
async def get_absentee_recap(session_id: UUID) -> AbsenteeRecap:
    """Return the stand-in turns and penalties that the session recorded. No turns returns an empty recap."""
    session = await _require_session(session_id)
    return build_absentee_recap(session.state)
