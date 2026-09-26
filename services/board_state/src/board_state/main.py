"""Board State Microservice - Powered by eventsource-py.

Manages tactical maps, token coordinates, collision rules, and fog-of-war.
"""

from typing import Literal
from uuid import NAMESPACE_DNS, UUID, uuid4, uuid5

from board_state.aggregate import BoardAggregate, BoardState, PlacedTokenState
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from runefoble_platform.event_sourcing import (
    AggregateRepository,
    create_aggregate_repository,
    get_event_store,
)

app = FastAPI(
    title="Runefoble - Board State Service",
    version="0.1.0",
    description="Tactical Map, Grid Coordinates, Token Management, and Spatial Queries backed by eventsource-py.",
)

# Global aggregate repository
repo: AggregateRepository[BoardAggregate] = create_aggregate_repository(BoardAggregate)


def to_board_uuid(session_id: str) -> UUID:
    """Deterministically convert session_id string or UUID into UUID."""
    try:
        return UUID(session_id)
    except ValueError:
        return uuid5(NAMESPACE_DNS, session_id)


class PlaceTokenRequest(BaseModel):
    token_id: str | None = None
    name: str
    token_type: Literal["pc", "monster", "npc", "obstacle"] = "pc"
    x: int
    y: int
    hp: int | None = None
    is_friendly: bool = True


class MoveTokenRequest(BaseModel):
    token_id: str
    to_x: int
    to_y: int
    initiated_by: Literal["player", "the_watcher", "stand_in"] = "player"


async def get_or_create_board(session_id: str) -> BoardAggregate:
    board_id = to_board_uuid(session_id)
    try:
        return await repo.load(board_id)
    except Exception:
        # Initialize default 12x12 grid with demo tokens for session
        board = BoardAggregate(board_id)
        board.initialize_grid(cols=12, rows=12, session_id=session_id)
        # Place standard tokens
        board.place_token("t1", name="Valeros", token_type="pc", x=2, y=3, is_friendly=True)
        board.place_token("t2", name="Kyra", token_type="pc", x=3, y=3, is_friendly=True)
        await repo.save(board)
        return board


@app.get("/healthz")
async def health_check():
    return {
        "status": "ok",
        "service": "board_state",
        "event_store": type(get_event_store()).__name__,
    }


@app.get("/api/v1/boards/{session_id}", response_model=BoardState)
async def get_board(session_id: str):
    board = await get_or_create_board(session_id)
    return board.state


@app.post("/api/v1/boards/{session_id}/tokens", response_model=PlacedTokenState)
async def place_token(session_id: str, req: PlaceTokenRequest):
    board = await get_or_create_board(session_id)
    token_id = req.token_id or str(uuid4())
    try:
        board.place_token(
            token_id=token_id,
            name=req.name,
            token_type=req.token_type,
            x=req.x,
            y=req.y,
            hp=req.hp,
            is_friendly=req.is_friendly,
        )
        await repo.save(board)
        return board.state.tokens[token_id]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.post("/api/v1/boards/{session_id}/move", response_model=PlacedTokenState)
async def move_token(session_id: str, req: MoveTokenRequest):
    board = await get_or_create_board(session_id)
    try:
        board.move_token(
            token_id=req.token_id,
            to_x=req.to_x,
            to_y=req.to_y,
            initiated_by=req.initiated_by,
        )
        await repo.save(board)
        return board.state.tokens[req.token_id]
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


def main():
    import uvicorn

    uvicorn.run("board_state.main:app", host="0.0.0.0", port=8002, reload=True)


if __name__ == "__main__":
    main()
