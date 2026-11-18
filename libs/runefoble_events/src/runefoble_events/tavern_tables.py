"""Multiplayer minigame table domain events (TASK-0566).

Table state (seats, chips, pot, bets, scores, dice, roulette and craps results)
is event-sourced on the TavernGame aggregate. Each event carries the outcome
decided by the command, so replaying events yields the same table state.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from pydantic import Field

from runefoble_events.base import BaseRunefobleEvent, register_event


@register_event
class TableOpened(BaseRunefobleEvent):
    """Fired when a minigame table is opened for an establishment."""

    aggregate_type: str = "TavernGame"
    aggregate_id: UUID = Field(default_factory=uuid4)
    game_id: UUID | str = ""
    establishment_id: str = "est-default"
    game_type: str = "darts"


@register_event
class TablePlayerSeated(BaseRunefobleEvent):
    """Fired when a player takes a seat at an open minigame table."""

    aggregate_type: str = "TavernGame"
    aggregate_id: UUID = Field(default_factory=uuid4)
    game_id: UUID | str = ""
    player_id: str
    name: str = "Player"
    chips: int = 100
    score: int = 501
    dice: list[int] = Field(default_factory=list)


@register_event
class TableBetPlaced(BaseRunefobleEvent):
    """Fired when a seated player places a wager on the table."""

    aggregate_type: str = "TavernGame"
    aggregate_id: UUID = Field(default_factory=uuid4)
    game_id: UUID | str = ""
    player_id: str
    amount: int
    bet_type: str = "straight"
    target: Any = None


@register_event
class DartThrown(BaseRunefobleEvent):
    """Fired when a seated player throws a dart in a 501 game."""

    aggregate_type: str = "TavernGame"
    aggregate_id: UUID = Field(default_factory=uuid4)
    game_id: UUID | str = ""
    player_id: str
    hit: dict[str, Any] = Field(default_factory=dict)
    score_remaining: int
    is_bust: bool = False
    is_won: bool = False
    next_turn_index: int = 0
    payout: int = 0


@register_event
class TableBidPlaced(BaseRunefobleEvent):
    """Fired when a player raises the Liar's Dice bid at a table."""

    aggregate_type: str = "TavernGame"
    aggregate_id: UUID = Field(default_factory=uuid4)
    game_id: UUID | str = ""
    player_id: str
    quantity: int
    face: int
    next_turn_index: int = 0


@register_event
class TableChallengeResolved(BaseRunefobleEvent):
    """Fired when a Liar's Dice bid is challenged and the loser loses a die."""

    aggregate_type: str = "TavernGame"
    aggregate_id: UUID = Field(default_factory=uuid4)
    game_id: UUID | str = ""
    challenger_id: str
    bidder_id: str
    loser_id: str
    winner_id: str
    loser_dice_after: list[int] = Field(default_factory=list)
    next_hands: dict[str, list[int]] = Field(default_factory=dict)
    champion_id: str | None = None
    payout: int = 0


@register_event
class RouletteSpun(BaseRunefobleEvent):
    """Fired when the roulette wheel is spun and bets are settled."""

    aggregate_type: str = "TavernGame"
    aggregate_id: UUID = Field(default_factory=uuid4)
    game_id: UUID | str = ""
    winning_number: int
    color: str
    payouts: dict[str, int] = Field(default_factory=dict)


@register_event
class CrapsRolled(BaseRunefobleEvent):
    """Fired when the craps dice are tumbled and the point phase is evaluated."""

    aggregate_type: str = "TavernGame"
    aggregate_id: UUID = Field(default_factory=uuid4)
    game_id: UUID | str = ""
    dice: list[int] = Field(default_factory=list)
    point: int | None = None
    payouts: dict[str, int] = Field(default_factory=dict)
    remaining_bets: list[dict[str, Any]] = Field(default_factory=list)
    narrative: str = ""


__all__ = [
    "CrapsRolled",
    "DartThrown",
    "RouletteSpun",
    "TableBetPlaced",
    "TableBidPlaced",
    "TableChallengeResolved",
    "TableOpened",
    "TablePlayerSeated",
]
