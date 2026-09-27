"""Pydantic state schemas and API request/response models for Board State microservice."""

from __future__ import annotations

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
from board_state.models.transitions import BoardTransitionsMixin
from board_state.models.vfx import (
    BoardDecalState,
    CastSpellRequest,
    CastSpellResponse,
    DecayDecalsRequest,
    FinishVFXRequest,
    FinishVFXResponse,
)

__all__ = [
    "AoEEvaluateRequest",
    "AoETemplatePlaceRequest",
    "AoETemplateResponse",
    "AoETemplateState",
    "BoardDecalState",
    "BoardState",
    "BoardTransitionsMixin",
    "CastSpellRequest",
    "CastSpellResponse",
    "ConfigureTerrainRequest",
    "CreateBoardRequest",
    "DecayDecalsRequest",
    "FinishVFXRequest",
    "FinishVFXResponse",
    "FogOfWarUpdateRequest",
    "MoveTokenRequest",
    "MoveTokenResponse",
    "PlaceTokenRequest",
    "PlacedTokenState",
    "TerrainCellState",
    "TerrainDict",
    "TokenActionRequest",
    "TokenActionResponse",
    "UVTTImportResponse",
    "VisibilityResponse",
]
