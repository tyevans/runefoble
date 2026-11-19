"""Multiplayer minigames tables: rules engine, table state model, and WebSocket plumbing."""

from game_session.minigame_tables.models import MinigameTableState, TablePlayer
from game_session.minigame_tables.rules_engine import (
    calculate_dart_trajectory,
    evaluate_craps_roll,
    evaluate_darts_501_throw,
    evaluate_roulette_bets,
    score_dart_hit,
)
from game_session.minigame_tables.ws_manager import minigame_table_manager

__all__ = [
    "MinigameTableState",
    "TablePlayer",
    "calculate_dart_trajectory",
    "evaluate_craps_roll",
    "evaluate_darts_501_throw",
    "evaluate_roulette_bets",
    "minigame_table_manager",
    "score_dart_hit",
]
