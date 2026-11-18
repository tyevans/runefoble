"""Maps minigame table WebSocket actions to TavernGame table commands (TASK-0566).

The acting player is always the verified socket principal. Message fields never name the actor,
and the server rolls the roulette wheel and the craps dice (TASK-0548).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from game_session.minigames import TavernGameAggregate

TableCommand = Callable[[TavernGameAggregate], dict[str, Any]]


def table_command_for(action: str, data: dict[str, Any], user_id: str) -> TableCommand | None:
    """Return the table command for a socket action, or None for a pass-through action."""
    if action == "join":
        player_id = user_id
        name = data.get("name", "Adventurer")
        chips = int(data.get("chips", 100))
        return lambda agg: agg.seat_player(player_id=player_id, name=name, chips=chips)
    if action == "bet":
        player_id = user_id
        amount = int(data.get("amount", 10))
        bet_type = data.get("bet_type", "straight")
        target = data.get("target")
        return lambda agg: agg.place_bet(
            player_id=player_id, amount=amount, bet_type=bet_type, target=target
        )
    if action == "throw_dart":
        player_id = user_id
        vx = float(data.get("vx", 0.0))
        vy = float(data.get("vy", 0.0))
        wind_x = float(data.get("wind_x", 0.0))
        wind_y = float(data.get("wind_y", 0.0))
        return lambda agg: agg.throw_dart(
            player_id=player_id, vx=vx, vy=vy, wind_x=wind_x, wind_y=wind_y
        )
    if action == "bid":
        player_id = user_id
        quantity = int(data.get("quantity", 1))
        face = int(data.get("face", 1))
        return lambda agg: agg.submit_table_bid(player_id=player_id, quantity=quantity, face=face)
    if action == "challenge":
        challenger_id = user_id
        return lambda agg: agg.challenge_bluff(challenger_id=challenger_id)
    if action == "spin_roulette":
        return lambda agg: agg.spin_roulette()
    if action == "roll_craps":
        return lambda agg: agg.roll_craps()
    return None


__all__ = ["TableCommand", "table_command_for"]
