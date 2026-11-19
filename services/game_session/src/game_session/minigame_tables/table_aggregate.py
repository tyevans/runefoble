"""Table commands and event appliers for multiplayer minigame tables (TASK-0566).

Mixed into TavernGameAggregate. Each command validates the request, decides the
outcome, and records it with create_event. Each @handles method applies the
recorded outcome to MinigameTableState. Commands never mutate table state
directly (Hard Invariant 2).
"""

from __future__ import annotations

import random
from typing import Any

from eventsource.domain.decorators import handles
from game_session.minigame_rules import count_matching_dice, roll_dice_hand, validate_liars_dice_bid
from game_session.minigame_tables.models import MinigameTableState, TablePlayer
from game_session.minigame_tables.rules_engine import (
    calculate_dart_trajectory,
    evaluate_craps_roll,
    evaluate_darts_501_throw,
    evaluate_roulette_bets,
    score_dart_hit,
)
from runefoble_events.events import (
    CrapsRolled,
    DartThrown,
    MinigameEnded,
    RouletteSpun,
    TableBetPlaced,
    TableBidPlaced,
    TableChallengeResolved,
    TableOpened,
    TablePlayerSeated,
)
from runefoble_platform.dice import roll_die


class TableCommandsMixin:
    """Table commands and @handles appliers. Requires the host to provide state and create_event."""

    def _table(self) -> MinigameTableState:
        table = self.state.table
        if table is None:
            raise ValueError("Table is not open")
        return table

    def _snapshot(self) -> dict[str, Any]:
        return self._table().model_dump()

    def _active_order(self) -> list[str]:
        table = self._table()
        return [pid for pid in table.player_order if not table.players[pid].eliminated]

    def _next_index(self, active_order: list[str]) -> int:
        """Advance the turn index one seat, or keep it when no seat is active."""
        current = self._table().current_turn_index
        return (current + 1) % len(active_order) if active_order else current

    # ------------------------------------------------------------------ commands

    def open_table(self, table_id: str, establishment_id: str, game_type: str) -> dict[str, Any]:
        if self.state.table is not None:
            raise ValueError(f"Table '{table_id}' is already open")
        self.create_event(
            TableOpened,
            game_id=table_id,
            establishment_id=establishment_id,
            game_type=game_type,
        )
        return self._snapshot()

    def seat_player(self, player_id: str, name: str, chips: int) -> dict[str, Any]:
        table = self._table()
        if player_id not in table.players:
            initial_dice = roll_dice_hand(5) if table.game_type == "liars_dice" else []
            self.create_event(
                TablePlayerSeated,
                game_id=table.table_id,
                player_id=player_id,
                name=name,
                chips=chips,
                score=501,
                dice=initial_dice,
            )
        return {
            "type": "player_joined",
            "table_id": table.table_id,
            "player_id": player_id,
            "name": name,
            "table_state": self._snapshot(),
        }

    def place_bet(
        self,
        player_id: str,
        amount: int,
        bet_type: str = "straight",
        target: Any = None,
    ) -> dict[str, Any]:
        table = self._table()
        player = table.players.get(player_id)
        if not player or player.chips < amount:
            chips = player.chips if player else 0
            raise ValueError(f"Player {player_id} has insufficient chips ({chips} < {amount})")
        self.create_event(
            TableBetPlaced,
            game_id=table.table_id,
            player_id=player_id,
            amount=amount,
            bet_type=bet_type,
            target=target,
        )
        table = self._table()
        return {
            "type": "bet_placed",
            "table_id": table.table_id,
            "player_id": player_id,
            "bet": {
                "player_id": player_id,
                "bet_type": bet_type,
                "amount": amount,
                "target": target,
            },
            "pot": table.pot,
            "chips_remaining": table.players[player_id].chips,
        }

    def throw_dart(
        self,
        player_id: str,
        vx: float,
        vy: float,
        wind_x: float = 0.0,
        wind_y: float = 0.0,
    ) -> dict[str, Any]:
        table = self._table()
        player = table.players.get(player_id)
        if not player:
            raise ValueError(f"Player {player_id} not at table")

        tx, ty = calculate_dart_trajectory(vx, vy, wind_x, wind_y)
        hit = score_dart_hit(tx, ty)
        new_score, is_bust, is_won = evaluate_darts_501_throw(player.score, hit["points"])
        active_order = self._active_order()
        next_index = self._next_index(active_order)
        next_turn = active_order[next_index] if active_order else None
        payout = table.pot if is_won else 0
        player_name = player.name

        self.create_event(
            DartThrown,
            game_id=table.table_id,
            player_id=player_id,
            hit=hit,
            score_remaining=new_score,
            is_bust=is_bust,
            is_won=is_won,
            next_turn_index=next_index,
            payout=payout,
        )
        result: dict[str, Any] = {
            "type": "dart_thrown",
            "table_id": table.table_id,
            "player_id": player_id,
            "hit": hit,
            "score_remaining": new_score,
            "is_bust": is_bust,
            "is_won": is_won,
            "next_turn": next_turn,
        }
        if is_won:
            self.create_event(
                MinigameEnded,
                game_id=table.table_id,
                winner_id=player_id,
                payout=payout,
                summary=f"{player_name} won darts 501 with payout {payout} chips!",
            )
            result["payout"] = payout
            result["winner_id"] = player_id
        return result

    def submit_table_bid(self, player_id: str, quantity: int, face: int) -> dict[str, Any]:
        table = self._table()
        if not validate_liars_dice_bid(table.current_bid, quantity, face):
            raise ValueError(
                f"Invalid bid {quantity}x {face}. Must escalate from {table.current_bid}"
            )
        active_order = self._active_order()
        next_index = self._next_index(active_order)
        self.create_event(
            TableBidPlaced,
            game_id=table.table_id,
            player_id=player_id,
            quantity=quantity,
            face=face,
            next_turn_index=next_index,
        )
        return {
            "type": "bid_placed",
            "table_id": table.table_id,
            "player_id": player_id,
            "bid": {"quantity": quantity, "face": face, "bidder": player_id},
            "next_turn": active_order[next_index] if active_order else None,
        }

    def challenge_bluff(self, challenger_id: str) -> dict[str, Any]:
        table = self._table()
        bid = table.current_bid
        if not bid:
            raise ValueError("No active bid to challenge")

        all_dice = [die for p in table.players.values() if not p.eliminated for die in p.dice]
        matching = count_matching_dice(all_dice, bid["face"])
        bid_true = matching >= bid["quantity"]
        bidder_id = bid["bidder"]
        loser_id = challenger_id if bid_true else bidder_id
        winner_id = bidder_id if bid_true else challenger_id

        loser_dice_after = table.players[loser_id].dice[:-1]
        post_dice = {
            pid: (loser_dice_after if pid == loser_id else p.dice)
            for pid, p in table.players.items()
        }
        survivors = [
            p
            for p in table.players.values()
            if not p.eliminated and not (p.player_id == loser_id and not loser_dice_after)
        ]
        is_game_over = len(survivors) <= 1
        champion = survivors[0] if is_game_over and survivors else None
        payout = table.pot if champion else 0
        next_hands = (
            {}
            if champion
            else {p.player_id: roll_dice_hand(len(post_dice[p.player_id])) for p in survivors}
        )

        self.create_event(
            TableChallengeResolved,
            game_id=table.table_id,
            challenger_id=challenger_id,
            bidder_id=bidder_id,
            loser_id=loser_id,
            winner_id=winner_id,
            loser_dice_after=loser_dice_after,
            next_hands=next_hands,
            champion_id=champion.player_id if champion else None,
            payout=payout,
        )
        if champion:
            self.create_event(
                MinigameEnded,
                game_id=table.table_id,
                winner_id=champion.player_id,
                payout=payout,
                summary=f"{champion.name} won Liar's Dice with payout {payout}!",
            )

        msg: dict[str, Any] = {
            "type": "challenge_resolved",
            "table_id": table.table_id,
            "challenger_id": challenger_id,
            "bidder_id": bidder_id,
            "bid": bid,
            "all_hands": post_dice,
            "matching_count": matching,
            "winner_id": winner_id,
            "loser_id": loser_id,
            "is_game_over": is_game_over,
        }
        if champion:
            msg["champion_id"] = champion.player_id
            msg["payout"] = payout
        return msg

    def spin_roulette(self) -> dict[str, Any]:
        table = self._table()
        win_num = random.SystemRandom().randint(0, 36)
        res = evaluate_roulette_bets(win_num, table.bets)
        self.create_event(
            RouletteSpun,
            game_id=table.table_id,
            winning_number=win_num,
            color=res["color"],
            payouts=res["payouts"],
        )
        table = self._table()
        return {
            "type": "wheel_spun",
            "table_id": table.table_id,
            "winning_number": win_num,
            "color": res["color"],
            "payouts": res["payouts"],
            "winning_bets": res["winning_bets"],
            "player_balances": {p.player_id: p.chips for p in table.players.values()},
        }

    def roll_craps(self) -> dict[str, Any]:
        table = self._table()
        rng = random.SystemRandom()
        actual_dice = [roll_die(6, rng), roll_die(6, rng)]
        new_point, payouts, _winning_bets, narrative = evaluate_craps_roll(
            actual_dice, table.point, table.bets
        )
        remaining = [
            b for b in table.bets if b.get("bet_type") == "pass_line" and new_point is not None
        ]
        self.create_event(
            CrapsRolled,
            game_id=table.table_id,
            dice=actual_dice,
            point=new_point,
            payouts=payouts,
            remaining_bets=remaining,
            narrative=narrative,
        )
        table = self._table()
        return {
            "type": "craps_rolled",
            "table_id": table.table_id,
            "dice": actual_dice,
            "total": sum(actual_dice),
            "point": table.point,
            "payouts": payouts,
            "narrative": narrative,
            "player_balances": {p.player_id: p.chips for p in table.players.values()},
        }

    # ------------------------------------------------------------------ appliers

    @handles(TableOpened)
    def handle_table_opened(self, event: TableOpened) -> None:
        table_id = str(event.game_id)
        self.state.game_id = table_id
        self.state.table = MinigameTableState(
            table_id=table_id,
            establishment_id=event.establishment_id,
            game_type=event.game_type,
        )

    @handles(TablePlayerSeated)
    def handle_player_seated(self, event: TablePlayerSeated) -> None:
        table = self._table()
        table.players[event.player_id] = TablePlayer(
            player_id=event.player_id,
            name=event.name,
            chips=event.chips,
            score=event.score,
            dice=list(event.dice),
        )
        table.player_order.append(event.player_id)

    @handles(TableBetPlaced)
    def handle_bet_placed(self, event: TableBetPlaced) -> None:
        table = self._table()
        table.players[event.player_id].chips -= event.amount
        table.pot += event.amount
        table.bets.append(
            {
                "player_id": event.player_id,
                "bet_type": event.bet_type,
                "amount": event.amount,
                "target": event.target,
            }
        )

    @handles(DartThrown)
    def handle_dart_thrown(self, event: DartThrown) -> None:
        table = self._table()
        player = table.players[event.player_id]
        player.score = event.score_remaining
        table.current_turn_index = event.next_turn_index
        table.round_number += 1
        if event.is_won:
            player.chips += event.payout
            table.status = "completed"

    @handles(TableBidPlaced)
    def handle_bid_placed(self, event: TableBidPlaced) -> None:
        table = self._table()
        table.current_bid = {
            "quantity": event.quantity,
            "face": event.face,
            "bidder": event.player_id,
        }
        table.current_turn_index = event.next_turn_index
        table.round_number += 1

    @handles(TableChallengeResolved)
    def handle_challenge_resolved(self, event: TableChallengeResolved) -> None:
        table = self._table()
        loser = table.players[event.loser_id]
        loser.dice = list(event.loser_dice_after)
        loser.eliminated = not loser.dice
        if event.champion_id:
            table.players[event.champion_id].chips += event.payout
            table.status = "completed"
        else:
            for pid, hand in event.next_hands.items():
                table.players[pid].dice = list(hand)
            table.current_bid = None

    @handles(RouletteSpun)
    def handle_roulette_spun(self, event: RouletteSpun) -> None:
        table = self._table()
        for pid, payout in event.payouts.items():
            if pid in table.players:
                table.players[pid].chips += payout
        table.bets.clear()
        table.pot = 0
        table.round_number += 1

    @handles(CrapsRolled)
    def handle_craps_rolled(self, event: CrapsRolled) -> None:
        table = self._table()
        for pid, payout in event.payouts.items():
            if pid in table.players:
                table.players[pid].chips += payout
        table.point = event.point
        table.bets = [dict(b) for b in event.remaining_bets]
        table.round_number += 1
