"""Pydantic data models and schemas for interactive merchant haggling.

Part of TASK-0262 / PRD-0024 / US-0075.
Governed by ADR-0001, ADR-0002, ADR-0004, ADR-0006, and ADR-0012.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class GambitType(StrEnum):
    FLATTERY = "flattery"
    BULK_ORDER_PROMISE = "bulk_order_promise"
    POINT_OUT_FLAW = "point_out_flaw"
    HARD_INTIMIDATION = "hard_intimidation"
    WALK_AWAY_BLUFF = "walk_away_bluff"

    @classmethod
    def normalize(cls, raw: str) -> GambitType:
        norm = raw.lower().strip().replace(" ", "_").replace("/", "_").replace("-", "_")
        if "flatter" in norm or "praise" in norm:
            return cls.FLATTERY
        if "bulk" in norm:
            return cls.BULK_ORDER_PROMISE
        if "flaw" in norm or "point" in norm:
            return cls.POINT_OUT_FLAW
        if "intimidat" in norm:
            return cls.HARD_INTIMIDATION
        if "walk" in norm or "bluff" in norm:
            return cls.WALK_AWAY_BLUFF
        for member in cls:
            if member.value in norm:
                return member
        return cls.FLATTERY


class MerchantTemperament(StrEnum):
    GREEDY = "greedy"
    STUBBORN = "stubborn"
    VAIN = "vain"
    GENEROUS = "generous"

    @classmethod
    def normalize(cls, raw: str) -> MerchantTemperament:
        norm = raw.lower().strip().replace(" ", "_").replace("-", "_")
        if "greedy" in norm:
            return cls.GREEDY
        if "stubborn" in norm or "gruff" in norm:
            return cls.STUBBORN
        if "vain" in norm or "pride" in norm:
            return cls.VAIN
        if "generous" in norm or "cheerful" in norm:
            return cls.GENEROUS
        return cls.STUBBORN


class GambitEvaluationResult(BaseModel):
    gambit: GambitType
    roll_value: int
    target_dc: int
    is_success: bool
    price_delta: int
    new_offer: int
    counter_price: int
    patience_delta: int
    new_patience: int
    mood_delta: float
    new_mood_score: float
    voice_bark: str
    status: str = "active"


class StartNegotiationRequest(BaseModel):
    character_id: str
    item_id: str
    item_name: str = ""
    initial_offer_gp: int | None = None
    offered_price: int | None = None
    base_price: int | None = None
    gambit: str | None = None
    charisma_modifier: int = 0
    roll_value: int | None = None
    dialogue: str = ""
    session_id: str = ""
    campaign_id: str = ""
    merchant_id: str | None = None
    merchant_name: str = "Merchant"
    temperament: str = "Stubborn"


class ExecuteGambitRequest(BaseModel):
    character_id: str
    gambit: str
    roll_value: int | None = None
    charisma_modifier: int = 0
    offered_price: int | None = None
    dialogue: str = ""


class DMOverrideRequest(BaseModel):
    action: str  # soothe_merchant, enrage_merchant, accept_deal, force_accept, refuse_kick_out, refuse, override_price, inject_bark
    override_price_gp: int | None = None
    override_price: int | None = None
    narrative_bark: str | None = None
    patience_delta: int = 0
    mood_delta: float = 0.0


class NegotiationSessionState(BaseModel):
    """Event-sourced state of a live merchant bartering interaction."""

    negotiation_id: str = ""
    session_id: str = ""
    campaign_id: str = ""
    establishment_id: str = ""
    merchant_id: str = ""
    merchant_name: str = "Merchant"
    character_id: str = ""
    item_id: str = ""
    item_name: str = "Item"
    original_price: int = 100
    current_offer: int = 100
    counter_price: int = 100
    base_margin: float = 0.20
    patience: int = 5
    temperament: str = "Stubborn"
    merchant_mood_score: float = 0.0
    status: str = "active"  # active, completed, refused, terminated
    last_bark: str = ""
    gambits_history: list[dict[str, Any]] = Field(default_factory=list)
    final_price: int | None = None


NegotiationSession = NegotiationSessionState
