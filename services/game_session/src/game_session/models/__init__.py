"""GameSession domain models, request/response schemas, and aggregate state."""

from __future__ import annotations

from game_session.models.combat import (
    CombatStateResponse,
    CombatTransitionsMixin,
    InitiativeRollRequest,
    NextTurnRequest,
    RollDiceRequest,
    RollDiceResponse,
    StartCombatRequest,
)
from game_session.models.director import AtmosphereUpdateRequest, DMOverrideRequest
from game_session.models.reaction_transitions import ReactionTransitionsMixin
from game_session.models.reactions import (
    DeclareReactionRequest,
    DeclareReactionResponse,
    EvaluateTriggersRequest,
    EvaluateTriggersResponse,
    ReadyActionRequest,
    ReadyActionResponse,
    ResolveReactionRequest,
    ResolveReactionResponse,
)
from game_session.models.session import (
    AutoPilotRequest,
    AutoPilotResponse,
    GameSessionState,
    HotSwapRequest,
    HotSwapResponse,
    JoinSessionRequest,
    LeaveSessionRequest,
    LeaveSessionResponse,
    ParticipantState,
    ReadinessRequest,
    SelectLobbyCharacterRequest,
)
from game_session.models.transitions import GameSessionTransitionsMixin

ResolveReactionResponse.model_rebuild(_types_namespace={"GameSessionState": GameSessionState})

__all__ = [
    "AtmosphereUpdateRequest",
    "AutoPilotRequest",
    "AutoPilotResponse",
    "CombatStateResponse",
    "CombatTransitionsMixin",
    "DeclareReactionRequest",
    "DMOverrideRequest",
    "DeclareReactionResponse",
    "EvaluateTriggersRequest",
    "EvaluateTriggersResponse",
    "GameSessionState",
    "GameSessionTransitionsMixin",
    "HotSwapRequest",
    "HotSwapResponse",
    "InitiativeRollRequest",
    "JoinSessionRequest",
    "LeaveSessionRequest",
    "LeaveSessionResponse",
    "NextTurnRequest",
    "ParticipantState",
    "ReadinessRequest",
    "SelectLobbyCharacterRequest",
    "ReactionTransitionsMixin",
    "ReadyActionRequest",
    "ReadyActionResponse",
    "ResolveReactionRequest",
    "ResolveReactionResponse",
    "RollDiceRequest",
    "RollDiceResponse",
    "StartCombatRequest",
]
