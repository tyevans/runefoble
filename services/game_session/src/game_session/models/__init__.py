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
    CreateSessionRequest,
    GameSessionState,
    HotSwapRequest,
    HotSwapResponse,
    JoinSessionRequest,
    LeaveSessionRequest,
    ParticipantState,
)
from game_session.models.settlement import (
    DEFAULT_FACILITIES,
    FACILITY_REST_BOONS,
    FACILITY_TIER_NAMES,
    CharterSettlementRequest,
    ClaimRestBoonRequest,
    SettlementState,
    UpgradeFacilityRequest,
)
from game_session.models.transitions import GameSessionTransitionsMixin

ResolveReactionResponse.model_rebuild(_types_namespace={"GameSessionState": GameSessionState})

__all__ = [
    "AutoPilotRequest",
    "AutoPilotResponse",
    "CharterSettlementRequest",
    "ClaimRestBoonRequest",
    "CombatStateResponse",
    "CombatTransitionsMixin",
    "CreateSessionRequest",
    "DEFAULT_FACILITIES",
    "DeclareReactionRequest",
    "DeclareReactionResponse",
    "EvaluateTriggersRequest",
    "EvaluateTriggersResponse",
    "FACILITY_REST_BOONS",
    "FACILITY_TIER_NAMES",
    "GameSessionState",
    "GameSessionTransitionsMixin",
    "HotSwapRequest",
    "HotSwapResponse",
    "InitiativeRollRequest",
    "JoinSessionRequest",
    "LeaveSessionRequest",
    "NextTurnRequest",
    "ParticipantState",
    "ReactionTransitionsMixin",
    "ReadyActionRequest",
    "ReadyActionResponse",
    "ResolveReactionRequest",
    "ResolveReactionResponse",
    "RollDiceRequest",
    "RollDiceResponse",
    "SettlementState",
    "StartCombatRequest",
    "UpgradeFacilityRequest",
]
