"""Board State Microservice.

Manages tactical maps, token coordinates, collision rules, and fog-of-war.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(
    title="Runefoble - Board State Service",
    version="0.1.0",
    description="Tactical Map, Grid Coordinates, Token Management, and Spatial Queries.",
)


class BoardToken(BaseModel):
    id: str
    session_id: str
    character_name: str
    x: int
    y: int
    color: str = "#3b82f6"
    is_ai_controlled: bool = False


class MoveTokenRequest(BaseModel):
    token_id: str
    to_x: int
    to_y: int


class TacticalBoard(BaseModel):
    session_id: str
    cols: int = 12
    rows: int = 12
    tokens: dict[str, BoardToken] = Field(default_factory=dict)


# In-memory board state store
boards: dict[str, TacticalBoard] = {}


def get_or_create_board(session_id: str) -> TacticalBoard:
    if session_id not in boards:
        board = TacticalBoard(session_id=session_id)
        # Prepopulate demo tokens
        t1 = BoardToken(
            id="t1", session_id=session_id, character_name="Valeros", x=2, y=3, color="#2563eb"
        )
        t2 = BoardToken(
            id="t2",
            session_id=session_id,
            character_name="Kyra",
            x=3,
            y=3,
            color="#db2777",
            is_ai_controlled=True,
        )
        board.tokens[t1.id] = t1
        board.tokens[t2.id] = t2
        boards[session_id] = board
    return boards[session_id]


@app.get("/healthz")
async def health_check():
    return {"status": "ok", "service": "board_state"}


@app.get("/api/v1/boards/{session_id}", response_model=TacticalBoard)
async def get_board(session_id: str):
    return get_or_create_board(session_id)


@app.post("/api/v1/boards/{session_id}/tokens", response_model=BoardToken)
async def add_token(session_id: str, token: BoardToken):
    board = get_or_create_board(session_id)
    board.tokens[token.id] = token
    return token


@app.post("/api/v1/boards/{session_id}/move", response_model=BoardToken)
async def move_token(session_id: str, req: MoveTokenRequest):
    board = get_or_create_board(session_id)
    if req.token_id not in board.tokens:
        raise HTTPException(status_code=404, detail="Token not found on board")

    # Boundary check
    if not (0 <= req.to_x < board.cols and 0 <= req.to_y < board.rows):
        raise HTTPException(status_code=400, detail="Target coordinates out of bounds")

    token = board.tokens[req.token_id]
    token.x = req.to_x
    token.y = req.to_y
    return token


def main():
    import uvicorn

    uvicorn.run("board_state.main:app", host="0.0.0.0", port=8002, reload=True)


if __name__ == "__main__":
    main()
