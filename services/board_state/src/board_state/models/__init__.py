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
from board_state.models.physics import (
    DiceSettledState,
    KnockbackRequest,
    KnockbackResponse,
    PhysicsCollisionState,
    SimulateThrowRequest,
    SimulateThrowResponse,
)
from board_state.models.terrain import (
    ConfigureTerrainRequest,
    TerrainCellState,
    TerrainDict,
    VisibilityResponse,
)
from board_state.models.tokens import (
    MoveResult,
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
from board_state.traps.models import (
    CreateTrapRequest,
    SecretTrapState,
    SwitchMapRequest,
    SwitchMapResponse,
    TrapListResponse,
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
    "CreateTrapRequest",
    "DecayDecalsRequest",
    "DiceSettledState",
    "FinishVFXRequest",
    "FinishVFXResponse",
    "FogOfWarUpdateRequest",
    "KnockbackRequest",
    "KnockbackResponse",
    "MoveResult",
    "MoveTokenRequest",
    "MoveTokenResponse",
    "PhysicsCollisionState",
    "PlaceTokenRequest",
    "PlacedTokenState",
    "SecretTrapState",
    "SimulateThrowRequest",
    "SimulateThrowResponse",
    "SwitchMapRequest",
    "SwitchMapResponse",
    "TerrainCellState",
    "TerrainDict",
    "TokenActionRequest",
    "TokenActionResponse",
    "TrapListResponse",
    "UVTTImportResponse",
    "VisibilityResponse",
]
