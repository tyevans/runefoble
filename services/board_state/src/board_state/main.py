"""Board State Microservice - Powered by eventsource-py.

Manages tactical maps, token coordinates, collision rules, and fog-of-war.
"""

from typing import Literal
from uuid import NAMESPACE_DNS, UUID, uuid4, uuid5

from board_state.aggregate import (
    BoardAggregate,
    BoardState,
    PlacedTokenState,
    TerrainCellState,
)
from fastapi import FastAPI, HTTPException, Query
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


class CreateBoardRequest(BaseModel):
    session_id: str | None = None
    board_id: str | None = None
    cols: int | None = None
    rows: int | None = None
    width: int | None = None
    height: int | None = None


class ConfigureTerrainRequest(BaseModel):
    x: int
    y: int
    elevation: int = 0
    terrain_type: str = "normal"
    hazard: str | None = None


class PlaceTokenRequest(BaseModel):
    token_id: str | None = None
    name: str
    token_type: Literal["pc", "monster", "npc", "obstacle"] = "pc"
    x: int
    y: int
    hp: int | None = None
    is_friendly: bool = True
    vision_radius: int = 2


class MoveTokenRequest(BaseModel):
    token_id: str | None = None
    to_x: int
    to_y: int
    initiated_by: Literal["player", "the_watcher", "stand_in"] = "player"
    movement_budget: int | None = None


class MoveTokenResponse(BaseModel):
    token_id: str
    name: str
    token_type: Literal["pc", "monster", "npc", "obstacle"] = "pc"
    x: int
    y: int
    hp: int | None = None
    is_friendly: bool = False
    vision_radius: int = 2
    active_hazard: str | None = None
    hazard_status: str | None = None
    movement_cost: int = 1
    hazard_triggered: str | None = None
    damage_dice: str | None = None


class VisibilityResponse(BaseModel):
    session_id: str
    cols: int
    rows: int
    fog_of_war_enabled: bool
    revealed_cells: list[list[int]]
    currently_visible_cells: list[list[int]]
    tokens: list[PlacedTokenState]


async def get_or_create_board(session_id: str) -> BoardAggregate:
    board_id = to_board_uuid(session_id)
    try:
        return await repo.load(board_id)
    except Exception:
        # Initialize default 12x12 grid with demo tokens for session
        board = BoardAggregate(board_id)
        board.initialize_grid(cols=12, rows=12, session_id=session_id)
        # Place standard tokens
        board.place_token(
            "t1", name="Valeros", token_type="pc", x=2, y=3, is_friendly=True, vision_radius=2
        )
        board.place_token(
            "t2", name="Kyra", token_type="pc", x=3, y=3, is_friendly=True, vision_radius=2
        )
        board.place_token(
            "t3", name="Goblin Scout", token_type="monster", x=8, y=8, is_friendly=False
        )
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


@app.get("/api/v1/boards/{session_id}/visibility", response_model=VisibilityResponse)
async def get_visibility(
    session_id: str, is_dm: bool = Query(False, description="Whether caller is Dungeon Master")
):
    """Compute fog-of-war visibility masks and filter hidden enemies."""
    board = await get_or_create_board(session_id)
    party_visible = board.compute_party_visibility()
    revealed_set = {tuple(c) for c in board.state.revealed_cells}

    # Filter tokens for player view if fog-of-war is active
    filtered_tokens: list[PlacedTokenState] = []
    for token in board.state.tokens.values():
        if (
            is_dm
            or token.is_friendly
            or not board.state.fog_of_war_enabled
            or (token.x, token.y) in revealed_set
        ):
            filtered_tokens.append(token)

    return VisibilityResponse(
        session_id=session_id,
        cols=board.state.cols,
        rows=board.state.rows,
        fog_of_war_enabled=board.state.fog_of_war_enabled,
        revealed_cells=board.state.revealed_cells,
        currently_visible_cells=party_visible,
        tokens=filtered_tokens,
    )


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
            vision_radius=req.vision_radius,
        )
        await repo.save(board)
        return board.state.tokens[token_id]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.post("/api/v1/boards", response_model=BoardState)
async def create_board(req: CreateBoardRequest):
    cols = req.cols or req.width or 10
    rows = req.rows or req.height or 10
    sess_id = req.session_id or req.board_id or str(uuid4())
    board_id = to_board_uuid(sess_id)
    board = BoardAggregate(board_id)
    board.initialize_grid(cols=cols, rows=rows, session_id=sess_id)
    await repo.save(board)
    return board.state


@app.post("/api/v1/boards/{session_id}/terrain", response_model=TerrainCellState)
async def configure_terrain(session_id: str, req: ConfigureTerrainRequest):
    board = await get_or_create_board(session_id)
    try:
        board.configure_terrain(
            x=req.x,
            y=req.y,
            elevation=req.elevation,
            terrain_type=req.terrain_type,
            hazard=req.hazard,
        )
        await repo.save(board)
        return board.get_terrain(req.x, req.y)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/api/v1/boards/{session_id}/tokens/{token_id}/move", response_model=MoveTokenResponse)
async def move_token_by_id(session_id: str, token_id: str, req: MoveTokenRequest):
    board = await get_or_create_board(session_id)
    try:
        cost, hazard_trig, dmg_dice = board.move_token(
            token_id=token_id,
            to_x=req.to_x,
            to_y=req.to_y,
            initiated_by=req.initiated_by,
            movement_budget=req.movement_budget,
        )
        await repo.save(board)
        tok = board.state.tokens[token_id]
        return MoveTokenResponse(
            token_id=tok.token_id,
            name=tok.name,
            token_type=tok.token_type,
            x=tok.x,
            y=tok.y,
            hp=tok.hp,
            is_friendly=tok.is_friendly,
            vision_radius=tok.vision_radius,
            active_hazard=tok.active_hazard,
            hazard_status=tok.hazard_status,
            movement_cost=cost,
            hazard_triggered=hazard_trig,
            damage_dice=dmg_dice,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/api/v1/boards/{session_id}/move", response_model=MoveTokenResponse)
async def move_token(session_id: str, req: MoveTokenRequest):
    if not req.token_id:
        raise HTTPException(status_code=400, detail="token_id is required")
    return await move_token_by_id(session_id, req.token_id, req)


@app.get("/ui/manifest")
def get_ui_manifest():
    """Advertise vendored microfrontend components for board state."""
    return {
        "service": "board_state",
        "package": "@runefoble/board-state-ui",
        "components": ["runefoble-board", "runefoble-map-uploader"],
        "version": "0.1.0",
    }


def main():
    import uvicorn

    uvicorn.run("board_state.main:app", host="0.0.0.0", port=8002, reload=True)


if __name__ == "__main__":
    main()
