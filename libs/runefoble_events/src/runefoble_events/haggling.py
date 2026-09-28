"""Domain events for interactive merchant haggling and DM arbitration engine."""

from __future__ import annotations

from typing import Any, ClassVar
from uuid import UUID, uuid4

from pydantic import Field

from runefoble_events.base import BaseRunefobleEvent, register_event


@register_event("runefoble.events.game_session.negotiation_session_started")
class NegotiationSessionStarted(BaseRunefobleEvent):
    """Fired when an interactive bartering / haggling session is initiated."""

    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "Negotiation"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.game_session.negotiation_session_started"
    negotiation_id: str
    session_id: str = ""
    campaign_id: str = ""
    establishment_id: str = ""
    merchant_id: str
    merchant_name: str = "Merchant"
    character_id: str
    item_id: str
    item_name: str
    original_price: int
    current_offer: int
    counter_price: int
    base_margin: float = 0.20
    patience: int = 5
    temperament: str = "Stubborn"
    merchant_mood_score: float = 0.0
    status: str = "active"
    metadata: dict[str, Any] = Field(default_factory=dict)


@register_event("runefoble.events.game_session.gambit_executed")
class GambitExecuted(BaseRunefobleEvent):
    """Fired when a bargaining gambit is attempted and resolved against merchant DC."""

    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "Negotiation"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.game_session.gambit_executed"
    negotiation_id: str
    character_id: str
    gambit: str
    roll_value: int
    target_dc: int
    is_success: bool
    price_delta: int = 0
    new_offer: int = 0
    counter_price: int = 0
    patience_delta: int = 0
    new_patience: int = 5
    mood_delta: float = 0.0
    merchant_mood_score: float = 0.0
    voice_bark: str = ""
    status: str = "active"
    metadata: dict[str, Any] = Field(default_factory=dict)


@register_event("runefoble.events.game_session.dm_negotiation_overridden")
class DMNegotiationOverridden(BaseRunefobleEvent):
    """Fired when the DM arbitrates or overrides haggling state in real time."""

    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "Negotiation"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.game_session.dm_negotiation_overridden"
    negotiation_id: str
    dm_user_id: str
    action: str  # "soothe_merchant", "enrage_merchant", "accept_deal", "refuse_kick_out", "override_price", "inject_bark"
    patience_delta: int = 0
    new_patience: int = 5
    mood_delta: float = 0.0
    new_mood_score: float = 0.0
    override_price: int | None = None
    narrative_bark: str = ""
    status: str = "active"
    metadata: dict[str, Any] = Field(default_factory=dict)


@register_event("runefoble.events.game_session.negotiation_concluded")
class NegotiationConcluded(BaseRunefobleEvent):
    """Fired when a bartering session concludes (accepted, refused, or terminated)."""

    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "Negotiation"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.game_session.negotiation_concluded"
    negotiation_id: str
    session_id: str = ""
    campaign_id: str = ""
    establishment_id: str = ""
    character_id: str
    merchant_id: str
    item_id: str
    item_name: str
    final_price: int = 0
    status: str = "completed"  # "completed", "refused", "terminated"
    currency_deducted: int = 0
    inventory_item_credited: str = ""
    closing_bark: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


@register_event("runefoble.events.character.currency_deducted")
class CurrencyDeducted(BaseRunefobleEvent):
    """Fired when player currency is deducted for a purchase or wager."""

    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "Negotiation"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.character.currency_deducted"
    character_id: str
    amount: int
    currency: str = "gp"
    reason: str = "merchant_purchase"
    session_id: str = ""
    campaign_id: str = ""


@register_event("runefoble.events.character.currency_credited")
class CurrencyCredited(BaseRunefobleEvent):
    """Fired when player currency is credited from sales or winnings."""

    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "Negotiation"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.character.currency_credited"
    character_id: str
    amount: int
    currency: str = "gp"
    reason: str = "merchant_sale"
    session_id: str = ""
    campaign_id: str = ""


# Aliases
NegotiationSessionStartedEvent = NegotiationSessionStarted
GambitExecutedEvent = GambitExecuted
DMNegotiationOverriddenEvent = DMNegotiationOverridden
NegotiationConcludedEvent = NegotiationConcluded
CurrencyDeductedEvent = CurrencyDeducted
CurrencyCreditedEvent = CurrencyCredited

__all__ = [
    "CurrencyCredited",
    "CurrencyCreditedEvent",
    "CurrencyDeducted",
    "CurrencyDeductedEvent",
    "DMNegotiationOverridden",
    "DMNegotiationOverriddenEvent",
    "GambitExecuted",
    "GambitExecutedEvent",
    "NegotiationConcluded",
    "NegotiationConcludedEvent",
    "NegotiationSessionStarted",
    "NegotiationSessionStartedEvent",
]
