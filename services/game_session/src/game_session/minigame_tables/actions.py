"""Turn and wagering action evaluators for minigame tables."""

from __future__ import annotations

import random
from typing import Any

from game_session.minigame_rules import count_matching_dice, roll_dice_hand, validate_liars_dice_bid
from game_session.minigame_tables.models import MinigameTableState
from game_session.minigame_tables.rules_engine import (
    calculate_dart_trajectory,
    evaluate_craps_roll,
    evaluate_darts_501_throw,
    evaluate_roulette_bets,
    score_dart_hit,
)
from runefoble_events.tavern import MinigameEnded, MinigameTurnTaken


def handle_throw_dart(
    table: MinigameTableState,
    player_id: str,
    vx: float,
    vy: float,
    wind_x: float = 0.0,
    wind_y: float = 0.0,
) -> tuple[dict[str, Any], list[Any]]:
    """Resolve a dart throw, calculate trajectory and score, update table state."""
    player = table.players.get(player_id)
    if not player:
        raise ValueError(f"Player {player_id} not at table")

    tx, ty = calculate_dart_trajectory(vx, vy, wind_x, wind_y)
    hit = score_dart_hit(tx, ty)
    new_score, is_bust, is_won = evaluate_darts_501_throw(player.score, hit["points"])
    player.score = new_score

    active_order = [pid for pid in table.player_order if not table.players[pid].eliminated]
    if active_order:
        table.current_turn_index = (table.current_turn_index + 1) % len(active_order)

    events: list[Any] = []
    result: dict[str, Any] = {
        "type": "dart_thrown",
        "table_id": table.table_id,
        "player_id": player_id,
        "hit": hit,
        "score_remaining": player.score,
        "is_bust": is_bust,
        "is_won": is_won,
        "next_turn": active_order[table.current_turn_index] if active_order else None,
    }

    if is_won:
        payout = table.pot
        player.chips += payout
        table.status = "completed"
        result["payout"] = payout
        result["winner_id"] = player_id
        events.append(
            MinigameEnded(
                game_id=table.table_id,
                winner_id=player_id,
                payout=payout,
                summary=f"{player.name} won darts 501 with payout {payout} chips!",
            )
        )

    events.append(
        MinigameTurnTaken(
            game_id=table.table_id,
            turn_number=table.round_number,
            actor_id=player_id,
            action_type="throw_dart",
            action_payload=hit,
            resulting_state={"score": player.score, "is_won": is_won},
        )
    )
    table.round_number += 1
    return result, events


def handle_liars_bid(
    table: MinigameTableState,
    player_id: str,
    quantity: int,
    face: int,
) -> tuple[dict[str, Any], list[Any]]:
    """Validate and register a Liar's Dice bid."""
    if not validate_liars_dice_bid(table.current_bid, quantity, face):
        raise ValueError(f"Invalid bid {quantity}x {face}. Must escalate from {table.current_bid}")

    bid = {"quantity": quantity, "face": face, "bidder": player_id}
    table.current_bid = bid
    active_order = [pid for pid in table.player_order if not table.players[pid].eliminated]
    table.current_turn_index = (table.current_turn_index + 1) % len(active_order)

    msg = {
        "type": "bid_placed",
        "table_id": table.table_id,
        "player_id": player_id,
        "bid": bid,
        "next_turn": active_order[table.current_turn_index] if active_order else None,
    }
    event = MinigameTurnTaken(
        game_id=table.table_id,
        turn_number=table.round_number,
        actor_id=player_id,
        action_type="bid",
        action_payload=bid,
        resulting_state={"current_bid": bid},
    )
    table.round_number += 1
    return msg, [event]


def handle_liars_challenge(
    table: MinigameTableState,
    challenger_id: str,
) -> tuple[dict[str, Any], list[Any]]:
    """Resolve a Liar's Dice challenge, eliminating dice or concluding the game."""
    if not table.current_bid:
        raise ValueError("No active bid to challenge")

    bid = table.current_bid
    all_dice = [die for p in table.players.values() if not p.eliminated for die in p.dice]
    target_face = bid["face"]
    bid_qty = bid["quantity"]
    bidder_id = bid["bidder"]

    matching = count_matching_dice(all_dice, target_face)
    bid_true = matching >= bid_qty
    loser_id = challenger_id if bid_true else bidder_id
    winner_id = bidder_id if bid_true else challenger_id

    loser = table.players[loser_id]
    if loser.dice:
        loser.dice.pop()
    if len(loser.dice) == 0:
        loser.eliminated = True

    survivors = [p for p in table.players.values() if not p.eliminated]
    is_game_over = len(survivors) <= 1

    msg: dict[str, Any] = {
        "type": "challenge_resolved",
        "table_id": table.table_id,
        "challenger_id": challenger_id,
        "bidder_id": bidder_id,
        "bid": bid,
        "all_hands": {p.player_id: p.dice for p in table.players.values()},
        "matching_count": matching,
        "winner_id": winner_id,
        "loser_id": loser_id,
        "is_game_over": is_game_over,
    }
    events: list[Any] = []

    if is_game_over and survivors:
        final_winner = survivors[0]
        final_winner.chips += table.pot
        table.status = "completed"
        msg["champion_id"] = final_winner.player_id
        msg["payout"] = table.pot
        events.append(
            MinigameEnded(
                game_id=table.table_id,
                winner_id=final_winner.player_id,
                payout=table.pot,
                summary=f"{final_winner.name} won Liar's Dice with payout {table.pot}!",
            )
        )
    else:
        for p in survivors:
            p.dice = roll_dice_hand(len(p.dice))
        table.current_bid = None

    return msg, events


def handle_spin_roulette(
    table: MinigameTableState,
    winning_number: int | None = None,
) -> tuple[dict[str, Any], list[Any]]:
    """Spin roulette wheel and disburse payouts."""
    win_num = winning_number if winning_number is not None else random.randint(0, 36)
    res = evaluate_roulette_bets(win_num, table.bets)

    for pid, payout in res["payouts"].items():
        if pid in table.players:
            table.players[pid].chips += payout

    table.bets.clear()
    table.pot = 0
    table.round_number += 1

    msg = {
        "type": "wheel_spun",
        "table_id": table.table_id,
        "winning_number": win_num,
        "color": res["color"],
        "payouts": res["payouts"],
        "winning_bets": res["winning_bets"],
        "player_balances": {p.player_id: p.chips for p in table.players.values()},
    }
    event = MinigameTurnTaken(
        game_id=table.table_id,
        turn_number=table.round_number,
        actor_id="croupier",
        action_type="spin_roulette",
        action_payload={"winning_number": win_num, "color": res["color"]},
        resulting_state={"payouts": res["payouts"]},
    )
    return msg, [event]


def handle_roll_craps(
    table: MinigameTableState,
    dice: list[int] | None = None,
) -> tuple[dict[str, Any], list[Any]]:
    """Tumble craps dice, evaluate point phase and field payouts."""
    actual_dice = dice if dice is not None else [random.randint(1, 6), random.randint(1, 6)]
    new_point, payouts, winning_bets, narrative = evaluate_craps_roll(
        actual_dice, table.point, table.bets
    )
    table.point = new_point

    for pid, payout in payouts.items():
        if pid in table.players:
            table.players[pid].chips += payout

    table.bets = [
        b for b in table.bets if b.get("bet_type") == "pass_line" and table.point is not None
    ]
    table.round_number += 1

    msg = {
        "type": "craps_rolled",
        "table_id": table.table_id,
        "dice": actual_dice,
        "total": sum(actual_dice),
        "point": table.point,
        "payouts": payouts,
        "narrative": narrative,
        "player_balances": {p.player_id: p.chips for p in table.players.values()},
    }
    return msg, []
