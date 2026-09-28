"""Multiplayer Table Manager for Tavern and Casino Minigames over WebSockets.

Governed by ADR-0004, ADR-0006, ADR-0012, and Hard Invariant 2 (domain events).
Synchronizes turn state, bets, dice rolls, and payouts across connected mobile clients.
"""

from __future__ import annotations

import contextlib
from typing import Any

from fastapi import WebSocket
from game_session.dependencies import STREAM_TAVERN, get_event_bus
from game_session.minigame_rules import roll_dice_hand
from game_session.minigame_tables.actions import (
    handle_liars_bid,
    handle_liars_challenge,
    handle_roll_craps,
    handle_spin_roulette,
    handle_throw_dart,
)
from game_session.minigame_tables.models import MinigameTableState, TablePlayer
from runefoble_events.tavern import MinigameStarted


class MinigameTableManager:
    """Manages active multiplayer minigame tables, WebSocket connections, and real-time state."""

    def __init__(self) -> None:
        self.tables: dict[str, MinigameTableState] = {}
        self.connections: dict[str, set[WebSocket]] = {}

    def get_or_create_table(
        self,
        table_id: str,
        establishment_id: str = "est-default",
        game_type: str = "darts",
    ) -> MinigameTableState:
        if table_id not in self.tables:
            self.tables[table_id] = MinigameTableState(
                table_id=table_id,
                establishment_id=establishment_id,
                game_type=game_type,
            )
        return self.tables[table_id]

    async def connect(self, table_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        if table_id not in self.connections:
            self.connections[table_id] = set()
        self.connections[table_id].add(websocket)

    def disconnect(self, table_id: str, websocket: WebSocket) -> None:
        if table_id in self.connections:
            self.connections[table_id].discard(websocket)
            if not self.connections[table_id]:
                del self.connections[table_id]

    async def broadcast(self, table_id: str, message: dict[str, Any]) -> None:
        sockets = list(self.connections.get(table_id, set()))
        dead: list[WebSocket] = []
        for ws in sockets:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(table_id, ws)

    async def join_player(
        self,
        table_id: str,
        player_id: str,
        name: str = "Player",
        chips: int = 100,
        establishment_id: str = "est-default",
        game_type: str = "darts",
    ) -> MinigameTableState:
        table = self.get_or_create_table(table_id, establishment_id, game_type)
        if player_id not in table.players:
            initial_dice = roll_dice_hand(5) if table.game_type == "liars_dice" else []
            table.players[player_id] = TablePlayer(
                player_id=player_id,
                name=name,
                chips=chips,
                score=501,
                dice=initial_dice,
            )
            table.player_order.append(player_id)

        await self._publish_events(
            [
                MinigameStarted(
                    game_id=table_id,
                    game_type=table.game_type,
                    wager_gold=table.pot,
                    initiator_id=table.player_order[0] if table.player_order else player_id,
                    challenger_id=player_id,
                    state_summary={"players": list(table.players.keys())},
                )
            ]
        )

        await self.broadcast(
            table_id,
            {
                "type": "player_joined",
                "table_id": table_id,
                "player_id": player_id,
                "name": name,
                "table_state": table.model_dump(),
            },
        )
        return table

    async def place_bet(
        self,
        table_id: str,
        player_id: str,
        amount: int,
        bet_type: str = "straight",
        target: Any = None,
    ) -> dict[str, Any]:
        table = self.tables[table_id]
        player = table.players.get(player_id)
        if not player or player.chips < amount:
            raise ValueError(
                f"Player {player_id} has insufficient chips ({player.chips if player else 0} < {amount})"
            )

        player.chips -= amount
        table.pot += amount
        bet_record = {
            "player_id": player_id,
            "bet_type": bet_type,
            "amount": amount,
            "target": target,
        }
        table.bets.append(bet_record)

        msg = {
            "type": "bet_placed",
            "table_id": table_id,
            "player_id": player_id,
            "bet": bet_record,
            "pot": table.pot,
            "chips_remaining": player.chips,
        }
        await self.broadcast(table_id, msg)
        return msg

    async def throw_dart(
        self,
        table_id: str,
        player_id: str,
        vx: float,
        vy: float,
        wind_x: float = 0.0,
        wind_y: float = 0.0,
    ) -> dict[str, Any]:
        table = self.tables[table_id]
        result, events = handle_throw_dart(table, player_id, vx, vy, wind_x, wind_y)
        await self._publish_events(events)
        await self.broadcast(table_id, result)
        return result

    async def submit_bid(
        self,
        table_id: str,
        player_id: str,
        quantity: int,
        face: int,
    ) -> dict[str, Any]:
        table = self.tables[table_id]
        msg, events = handle_liars_bid(table, player_id, quantity, face)
        await self._publish_events(events)
        await self.broadcast(table_id, msg)
        return msg

    async def challenge_bluff(self, table_id: str, challenger_id: str) -> dict[str, Any]:
        table = self.tables[table_id]
        msg, events = handle_liars_challenge(table, challenger_id)
        await self._publish_events(events)
        await self.broadcast(table_id, msg)
        return msg

    async def spin_roulette(
        self,
        table_id: str,
        winning_number: int | None = None,
    ) -> dict[str, Any]:
        table = self.tables[table_id]
        msg, events = handle_spin_roulette(table, winning_number)
        await self._publish_events(events)
        await self.broadcast(table_id, msg)
        return msg

    async def roll_craps(
        self,
        table_id: str,
        dice: list[int] | None = None,
    ) -> dict[str, Any]:
        table = self.tables[table_id]
        msg, events = handle_roll_craps(table, dice)
        await self._publish_events(events)
        await self.broadcast(table_id, msg)
        return msg

    async def _publish_events(self, events: list[Any]) -> None:
        bus = get_event_bus()
        if bus:
            for ev in events:
                with contextlib.suppress(Exception):
                    await bus.publish_event(STREAM_TAVERN, ev)


minigame_table_manager = MinigameTableManager()
