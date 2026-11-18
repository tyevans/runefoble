"""Tavern minigames, drinking contest, and merchant haggling domain events."""

from __future__ import annotations

from typing import Any, ClassVar
from uuid import UUID, uuid4

from pydantic import Field

from runefoble_events.base import BaseRunefobleEvent, register_event


@register_event("runefoble.events.tavern.minigame_started")
class MinigameStarted(BaseRunefobleEvent):
    """Fired when an interactive tavern minigame is commenced."""

    suppress_event_type_warning: ClassVar[bool] = True
    event_type: str = "runefoble.events.tavern.minigame_started"

    aggregate_type: str = "TavernGame"
    aggregate_id: UUID = Field(default_factory=uuid4)
    game_id: UUID | str = ""
    session_id: UUID | str | None = None
    campaign_id: UUID | str | None = None
    game_type: str = "liars_dice"  # liars_dice, card_duel, drinking_contest
    wager_gold: int = 0
    initiator_id: str
    challenger_id: str
    state_summary: dict[str, Any] = Field(default_factory=dict)


@register_event("runefoble.events.tavern.minigame_turn_taken")
class MinigameTurnTaken(BaseRunefobleEvent):
    """Fired when a participant submits a move or wager turn in a tavern minigame."""

    suppress_event_type_warning: ClassVar[bool] = True
    event_type: str = "runefoble.events.tavern.minigame_turn_taken"

    aggregate_type: str = "TavernGame"
    aggregate_id: UUID = Field(default_factory=uuid4)
    game_id: UUID | str = ""
    session_id: UUID | str | None = None
    turn_number: int = 1
    actor_id: str
    action_type: str  # bid, challenge, play_card, drink, pass
    action_payload: dict[str, Any] = Field(default_factory=dict)
    resulting_state: dict[str, Any] = Field(default_factory=dict)
    voice_bark: str | None = None


@register_event("runefoble.events.tavern.minigame_ended")
class MinigameEnded(BaseRunefobleEvent):
    """Fired when a minigame resolves, awarding winnings or penalties."""

    suppress_event_type_warning: ClassVar[bool] = True
    event_type: str = "runefoble.events.tavern.minigame_ended"

    aggregate_type: str = "TavernGame"
    aggregate_id: UUID = Field(default_factory=uuid4)
    game_id: UUID | str = ""
    session_id: UUID | str | None = None
    winner_id: str | None = None
    loser_id: str | None = None
    wager_gold: int = 0
    payout: int = 0
    voice_bark: str | None = None
    summary: str = ""


@register_event("runefoble.events.tavern.intoxication_level_changed")
class IntoxicationLevelChanged(BaseRunefobleEvent):
    """Fired when alcohol intake alters a character's intoxication stage and speech filters."""

    suppress_event_type_warning: ClassVar[bool] = True
    event_type: str = "runefoble.events.tavern.intoxication_level_changed"

    aggregate_type: str = "TavernGame"
    aggregate_id: UUID = Field(default_factory=uuid4)
    game_id: UUID | str = ""
    session_id: UUID | str | None = None
    character_id: str
    intoxication_level: str  # sober, tipsy, drunk, smashed, blackout
    constitution_dc: int = 10
    consecutive_drinks: int = 1
    dsp_filters: list[str] = Field(default_factory=list)


@register_event("runefoble.events.tavern.merchant_created")
class MerchantCreated(BaseRunefobleEvent):
    """Fired once when a merchant is first recorded, before its first negotiation."""

    suppress_event_type_warning: ClassVar[bool] = True
    event_type: str = "runefoble.events.tavern.merchant_created"

    aggregate_type: str = "Merchant"
    aggregate_id: UUID = Field(default_factory=uuid4)
    merchant_id: str
    name: str
    temperament: str = "stubborn_greedy"  # generous, shrewd, hostile, gullible, stubborn_greedy


@register_event("runefoble.events.tavern.haggling_negotiated")
class HagglingNegotiated(BaseRunefobleEvent):
    """Fired when a social bargaining roll or dialogue offer is evaluated by a merchant."""

    suppress_event_type_warning: ClassVar[bool] = True
    event_type: str = "runefoble.events.tavern.haggling_negotiated"

    aggregate_type: str = "Merchant"
    aggregate_id: UUID = Field(default_factory=uuid4)
    merchant_id: str
    session_id: UUID | str | None = None
    campaign_id: UUID | str | None = None
    character_id: str
    item_name: str
    base_price: int
    offered_price: int
    counter_price: int | None = None
    agreed_price: int | None = None
    merchant_mood: str = "shrewd"  # generous, shrewd, hostile, gullible, stubborn_greedy
    mood_score: float = 0.0
    outcome: str = "countered"  # accepted, countered, rejected, insulted
    dialogue: str = ""
    voice_bark: str | None = None


__all__ = [
    "HagglingNegotiated",
    "IntoxicationLevelChanged",
    "MerchantCreated",
    "MinigameEnded",
    "MinigameStarted",
    "MinigameTurnTaken",
]
