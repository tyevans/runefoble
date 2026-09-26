"""Tavern minigames, drinking contest, and merchant haggling domain events."""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from pydantic import Field

from runefoble_events.base import BaseRunefobleEvent, register_event


@register_event
class MinigameStarted(BaseRunefobleEvent):
    """Fired when an interactive tavern minigame is commenced."""

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


@register_event
class MinigameTurnTaken(BaseRunefobleEvent):
    """Fired when a participant submits a move or wager turn in a tavern minigame."""

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


@register_event
class MinigameEnded(BaseRunefobleEvent):
    """Fired when a minigame resolves, awarding winnings or penalties."""

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


@register_event
class IntoxicationLevelChanged(BaseRunefobleEvent):
    """Fired when alcohol intake alters a character's intoxication stage and speech filters."""

    aggregate_type: str = "TavernGame"
    aggregate_id: UUID = Field(default_factory=uuid4)
    game_id: UUID | str = ""
    session_id: UUID | str | None = None
    character_id: str
    intoxication_level: str  # sober, tipsy, drunk, smashed, blackout
    constitution_dc: int = 10
    consecutive_drinks: int = 1
    dsp_filters: list[str] = Field(default_factory=list)


@register_event
class HagglingNegotiated(BaseRunefobleEvent):
    """Fired when a social bargaining roll or dialogue offer is evaluated by a merchant."""

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
    "MinigameEnded",
    "MinigameStarted",
    "MinigameTurnTaken",
]
