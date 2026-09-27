"""Blackbox tests and modular decomposition invariants for board_state.models."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
from board_state.main import app as board_app
from httpx import ASGITransport, AsyncClient

REPO_ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = REPO_ROOT / "services/board_state/src/board_state/models"
FACADE_FILE = REPO_ROOT / "services/board_state/src/board_state/models.py"


def test_models_file_length_invariants():
    """Verify all models submodules and facade are strictly under their line limits."""
    # Check facade re-export file (< 80 lines)
    assert FACADE_FILE.is_file(), f"Facade file {FACADE_FILE} must exist"
    facade_lines = len(FACADE_FILE.read_text(encoding="utf-8").splitlines())
    assert facade_lines < 80, f"Facade models.py is {facade_lines} lines; must be < 80 lines"

    # Check package submodules (< 200 lines each, specific submodules < 100 lines)
    submodules = [
        "terrain.py",
        "tokens.py",
        "vfx.py",
        "actions.py",
        "board.py",
        "transitions.py",
        "__init__.py",
    ]

    for filename in submodules:
        file_path = MODELS_DIR / filename
        assert file_path.is_file(), f"Submodule {file_path} must exist"
        lines = len(file_path.read_text(encoding="utf-8").splitlines())
        assert lines < 200, f"{filename} is {lines} lines; exceeds 200 lines limit"
        if filename in ["terrain.py", "tokens.py", "vfx.py", "actions.py", "board.py"]:
            assert lines < 100, f"{filename} is {lines} lines; exceeds 100 lines target"


def test_facade_re_exports_backward_compatibility():
    """Verify importing from board_state.models exposes all public schemas and DTOs."""
    from board_state.models import (
        AoEEvaluateRequest,
        AoETemplatePlaceRequest,
        AoETemplateResponse,
        AoETemplateState,
        BoardDecalState,
        BoardState,
        BoardTransitionsMixin,
        CastSpellRequest,
        CastSpellResponse,
        ConfigureTerrainRequest,
        CreateBoardRequest,
        DecayDecalsRequest,
        FinishVFXRequest,
        FinishVFXResponse,
        FogOfWarUpdateRequest,
        MoveTokenRequest,
        MoveTokenResponse,
        PlacedTokenState,
        PlaceTokenRequest,
        TerrainCellState,
        TerrainDict,
        TokenActionRequest,
        TokenActionResponse,
        UVTTImportResponse,
        VisibilityResponse,
    )

    symbols = [
        AoEEvaluateRequest,
        AoETemplatePlaceRequest,
        AoETemplateResponse,
        AoETemplateState,
        BoardDecalState,
        BoardState,
        BoardTransitionsMixin,
        CastSpellRequest,
        CastSpellResponse,
        ConfigureTerrainRequest,
        CreateBoardRequest,
        DecayDecalsRequest,
        FinishVFXRequest,
        FinishVFXResponse,
        FogOfWarUpdateRequest,
        MoveTokenRequest,
        MoveTokenResponse,
        PlaceTokenRequest,
        PlacedTokenState,
        TerrainCellState,
        TerrainDict,
        TokenActionRequest,
        TokenActionResponse,
        UVTTImportResponse,
        VisibilityResponse,
    ]
    for sym in symbols:
        assert sym is not None


def test_modular_submodule_imports():
    """Verify importing from dedicated submodules works cleanly."""
    from board_state.models.actions import (
        AoEEvaluateRequest,
        AoETemplatePlaceRequest,
        AoETemplateResponse,
        AoETemplateState,
        TokenActionRequest,
        TokenActionResponse,
    )
    from board_state.models.board import (
        BoardState,
        CreateBoardRequest,
        FogOfWarUpdateRequest,
        UVTTImportResponse,
    )
    from board_state.models.terrain import (
        ConfigureTerrainRequest,
        TerrainCellState,
        TerrainDict,
        VisibilityResponse,
    )
    from board_state.models.tokens import (
        MoveTokenRequest,
        MoveTokenResponse,
        PlacedTokenState,
        PlaceTokenRequest,
    )
    from board_state.models.vfx import (
        BoardDecalState,
        CastSpellRequest,
        CastSpellResponse,
        DecayDecalsRequest,
        FinishVFXRequest,
        FinishVFXResponse,
    )

    symbols = [
        AoEEvaluateRequest,
        AoETemplatePlaceRequest,
        AoETemplateResponse,
        AoETemplateState,
        TokenActionRequest,
        TokenActionResponse,
        BoardState,
        CreateBoardRequest,
        FogOfWarUpdateRequest,
        UVTTImportResponse,
        ConfigureTerrainRequest,
        TerrainCellState,
        TerrainDict,
        VisibilityResponse,
        MoveTokenRequest,
        MoveTokenResponse,
        PlaceTokenRequest,
        PlacedTokenState,
        BoardDecalState,
        CastSpellRequest,
        CastSpellResponse,
        DecayDecalsRequest,
        FinishVFXRequest,
        FinishVFXResponse,
    ]
    for s in symbols:
        assert s is not None


def test_board_state_transitions_behavior():
    """Verify BoardState state transitions and mutation helpers execute accurately."""
    from board_state.models.board import BoardState
    from board_state.models.tokens import PlacedTokenState

    board = BoardState.initial(uuid4(), session_id="test-session-123", cols=10, rows=10)
    assert board.cols == 10
    assert board.rows == 10
    assert len(board.tokens) == 0

    # Place token
    hero = PlacedTokenState(token_id="hero-1", name="Valeros", x=1, y=1)
    board = board.with_token_placed(hero)
    assert "hero-1" in board.tokens

    # Move token
    board = board.with_token_moved("hero-1", to_x=3, to_y=4, active_hazard=None)
    assert board.tokens["hero-1"].x == 3
    assert board.tokens["hero-1"].y == 4

    # Fog reveal
    board = board.with_fog_revealed([[3, 4], [3, 5]])
    assert [3, 4] in board.revealed_cells
    assert [3, 5] in board.revealed_cells

    # Terrain modify
    board = board.with_terrain_modified(x=3, y=4, elevation=2, terrain_type="lava", hazard="fire")
    assert "fire" in board.active_hazards
    assert board.terrain_cells[(3, 4)].elevation == 2

    # Decals and decay
    board = board.with_area_effect([[3, 4]], decal_type="scorched_earth", decal_duration_rounds=2)
    assert len(board.active_decals) == 1
    board = board.with_decals_decayed(rounds=1)
    assert len(board.active_decals) == 1
    assert board.active_decals[0].rounds_remaining == 1
    board = board.with_decals_decayed(rounds=1)
    assert len(board.active_decals) == 0


@pytest.mark.asyncio
async def test_frontdoor_board_endpoints():
    """Verify frontdoor HTTP operations through public REST endpoints."""
    transport = ASGITransport(app=board_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Get board state
        res = await client.get("/api/v1/boards/session-test-modular")
        assert res.status_code == 200
        data = res.json()
        assert data["session_id"] == "session-test-modular"

        # Place token
        place_res = await client.post(
            "/api/v1/boards/session-test-modular/tokens",
            json={"token_id": "tok-mod-1", "name": "Rogue", "x": 2, "y": 2},
        )
        assert place_res.status_code == 200

        # Move token
        move_res = await client.post(
            "/api/v1/boards/session-test-modular/move",
            json={"token_id": "tok-mod-1", "to_x": 3, "to_y": 3},
        )
        assert move_res.status_code == 200
        moved = move_res.json()
        assert moved["x"] == 3
        assert moved["y"] == 3

        # Configure terrain
        terrain_res = await client.post(
            "/api/v1/boards/session-test-modular/terrain",
            json={"x": 3, "y": 3, "elevation": 1, "terrain_type": "stone", "hazard": None},
        )
        assert terrain_res.status_code == 200
