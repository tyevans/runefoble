"""Domain models and state representations for multiplayer minigame tables."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class TablePlayer(BaseModel):
    """Participant seated at a minigame table."""

    player_id: str
    name: str = "Player"
    chips: int = 100
    score: int = 501  # For darts
    dice: list[int] = Field(default_factory=list)  # For Liar's Dice
    eliminated: bool = False


class MinigameTableState(BaseModel):
    """Synchronized multiplayer game state for an establishment or casino table."""

    table_id: str
    establishment_id: str = "est-default"
    game_type: str = "darts"  # darts, liars_dice, roulette, craps
    status: str = "active"
    pot: int = 0
    players: dict[str, TablePlayer] = Field(default_factory=dict)
    player_order: list[str] = Field(default_factory=list)
    current_turn_index: int = 0
    bets: list[dict[str, Any]] = Field(default_factory=list)
    round_number: int = 1
    point: int | None = None  # Craps
    current_bid: dict[str, Any] | None = None  # Liar's Dice
    last_action: dict[str, Any] | None = None
