"""Game Session Microservice.

Coordinates active sessions, participant presence, turn order, and campaign timelines.
"""

from typing import Dict, List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(
    title="Runefoble - Game Session Service",
    version="0.1.0",
    description="Session Lifecycle, Turn / Initiative Order, and Live Participation.",
)


class SessionParticipant(BaseModel):
    user_id: str
    username: str
    role: str  # "dm", "player", "spectator"
    is_present: bool = True
    assigned_character_id: Optional[str] = None
    is_ai_stand_in_active: bool = False


class GameSession(BaseModel):
    id: str
    campaign_id: str
    title: str
    status: str = "active"  # "lobby", "active", "paused", "ended"
    round: int = 1
    current_turn_index: int = 0
    initiative_order: List[str] = Field(default_factory=list)
    participants: Dict[str, SessionParticipant] = Field(default_factory=dict)


# In-memory sessions store
sessions: Dict[str, GameSession] = {
    "sess-001": GameSession(
        id="sess-001",
        campaign_id="camp1",
        title="Tomb of the Star-Eater - Session 14",
        status="active",
        round=3,
        current_turn_index=0,
        initiative_order=["c1", "c2", "goblin-1"],
        participants={
            "user1": SessionParticipant(user_id="user1", username="Alice", role="player", assigned_character_id="c1"),
            "user2": SessionParticipant(
                user_id="user2",
                username="Bob",
                role="player",
                is_present=False,
                assigned_character_id="c2",
                is_ai_stand_in_active=True,
            ),
        },
    )
}


@app.get("/healthz")
async def health_check():
    return {"status": "ok", "service": "game_session"}


@app.get("/api/v1/sessions/{session_id}", response_model=GameSession)
async def get_session(session_id: str):
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    return sessions[session_id]


@app.post("/api/v1/sessions/{session_id}/next-turn", response_model=GameSession)
async def advance_turn(session_id: str):
    """Advance to the next participant in the initiative order."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    sess = sessions[session_id]
    if sess.initiative_order:
        sess.current_turn_index = (sess.current_turn_index + 1) % len(sess.initiative_order)
        if sess.current_turn_index == 0:
            sess.round += 1
    return sess


def main():
    import uvicorn
    uvicorn.run("game_session.main:app", host="0.0.0.0", port=8004, reload=True)


if __name__ == "__main__":
    main()
