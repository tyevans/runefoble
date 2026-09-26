"""Game Session Microservice - Powered by eventsource-py.

Coordinates active sessions, participant presence, turn order, and campaign timelines.
"""

from uuid import UUID, uuid4

from fastapi import FastAPI, HTTPException
from game_session.aggregate import GameSessionAggregate, GameSessionState
from pydantic import BaseModel
from runefoble_platform.event_sourcing import (
    AggregateRepository,
    create_aggregate_repository,
    get_event_store,
)

app = FastAPI(
    title="Runefoble - Game Session Service",
    version="0.1.0",
    description="Session Lifecycle, Turn / Initiative Order, and Live Participation backed by eventsource-py.",
)

# Global aggregate repository
repo: AggregateRepository[GameSessionAggregate] = create_aggregate_repository(GameSessionAggregate)


class CreateSessionRequest(BaseModel):
    campaign_id: UUID
    title: str = "Tomb of the Star-Eater - Session 1"
    dm_id: str = "the_watcher"


class JoinSessionRequest(BaseModel):
    player_id: str
    character_id: UUID
    character_name: str
    character_class: str


class LeaveSessionRequest(BaseModel):
    player_id: str
    reason: str = "disconnected"


@app.get("/healthz")
async def health_check():
    return {
        "status": "ok",
        "service": "game_session",
        "event_store": type(get_event_store()).__name__,
    }


@app.post("/api/v1/sessions/create", response_model=GameSessionState)
async def create_session(req: CreateSessionRequest):
    """Create a new event-sourced game session."""
    session_id = uuid4()
    session = GameSessionAggregate(session_id)
    session.create(campaign_id=req.campaign_id, title=req.title, dm_id=req.dm_id)
    await repo.save(session)
    return session.state


@app.get("/api/v1/sessions/{session_id}", response_model=GameSessionState)
async def get_session(session_id: UUID):
    """Load session state reconstituted from the event stream."""
    try:
        session = await repo.load(session_id)
        return session.state
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Session not found: {e}") from e


@app.post("/api/v1/sessions/{session_id}/start", response_model=GameSessionState)
async def start_session(session_id: UUID):
    """Transition session from lobby to active."""
    try:
        session = await repo.load(session_id)
        session.start()
        await repo.save(session)
        return session.state
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.post("/api/v1/sessions/{session_id}/join", response_model=GameSessionState)
async def join_session(session_id: UUID, req: JoinSessionRequest):
    """Record player entering session."""
    try:
        session = await repo.load(session_id)
        session.join_player(
            player_id=req.player_id,
            character_id=req.character_id,
            character_name=req.character_name,
            character_class=req.character_class,
        )
        await repo.save(session)
        return session.state
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.post("/api/v1/sessions/{session_id}/leave", response_model=GameSessionState)
async def leave_session(session_id: UUID, req: LeaveSessionRequest):
    """Record player absence, marking character for AI stand-in."""
    try:
        session = await repo.load(session_id)
        session.leave_player(player_id=req.player_id, reason=req.reason)
        await repo.save(session)
        return session.state
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.post("/api/v1/sessions/{session_id}/next-turn", response_model=GameSessionState)
async def advance_turn(session_id: UUID):
    """Advance to the next turn in the session."""
    try:
        session = await repo.load(session_id)
        session.advance_turn()
        await repo.save(session)
        return session.state
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


def main():
    import uvicorn

    uvicorn.run("game_session.main:app", host="0.0.0.0", port=8004, reload=True)


if __name__ == "__main__":
    main()
