"""Blackbox WebSocket test suite for multiplayer tavern and casino minigames.

Part of TASK-0264 / PRD-0024 / US-0074.
Governed by ADR-0001 (SpiceDB Zanzibar), ADR-0002 (Domain Events via eventsource-py),
ADR-0004 (Lit Web Components), ADR-0006 (Redis Streams), and ADR-0008 (Blackbox Testing).
"""

from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from game_session.dependencies import (
    set_event_bus,
)
from game_session.dependencies import (
    set_spicedb_client as set_session_spicedb,
)
from game_session.main import app as session_app
from gateway_api.auth import set_spicedb_client as set_gateway_spicedb
from runefoble_auth.spicedb import MockSpiceDBClient
from runefoble_platform.mock_redis import MockAsyncRedis
from runefoble_platform.redis_bus import RedisStreamsEventBus


@pytest.fixture
def mock_bus():
    redis_client = MockAsyncRedis()
    bus = RedisStreamsEventBus(client=redis_client)
    set_event_bus(bus)
    yield redis_client
    set_event_bus(None)


@pytest.fixture
def spicedb():
    mock_db = MockSpiceDBClient()
    set_session_spicedb(mock_db)
    set_gateway_spicedb(mock_db)
    yield mock_db
    set_session_spicedb(MockSpiceDBClient())
    set_gateway_spicedb(MockSpiceDBClient())


@pytest.fixture(autouse=True)
def clean_minigame_state():
    from game_session.minigame_tables.ws_manager import minigame_table_manager

    minigame_table_manager.tables.clear()
    minigame_table_manager.connections.clear()
    yield
    minigame_table_manager.tables.clear()
    minigame_table_manager.connections.clear()


def test_darts_and_billiards_multiplayer_turn_sync(
    spicedb: MockSpiceDBClient, mock_bus: MockAsyncRedis
) -> None:
    """Multiple player connections exchanging touch trajectory vectors in darts and billiards."""
    # ---------------- 1. Darts Multiplayer Turn Synchronization ----------------
    darts_table_id = f"table-darts-{uuid4().hex[:6]}"
    est_id = "est-salty-siren"

    asyncio.run(spicedb.write_relationship("establishment", est_id, "patron", "user", "archer_kip"))
    asyncio.run(
        spicedb.write_relationship("establishment", est_id, "patron", "user", "ranger_lyra")
    )

    with (
        TestClient(session_app) as client_darts,
        client_darts.websocket_connect(
            f"/ws/establishments/{est_id}/tables/{darts_table_id}?user_id=archer_kip"
        ) as ws_kip,
    ):
        assert ws_kip.receive_json()["type"] == "connected"
        ws_kip.send_json(
            {
                "action": "join",
                "player_id": "archer_kip",
                "name": "Kip",
                "chips": 100,
                "game_type": "darts",
            }
        )
        assert ws_kip.receive_json()["type"] == "player_joined"

        with client_darts.websocket_connect(
            f"/ws/establishments/{est_id}/tables/{darts_table_id}?user_id=ranger_lyra"
        ) as ws_lyra:
            assert ws_lyra.receive_json()["type"] == "connected"
            ws_lyra.send_json(
                {
                    "action": "join",
                    "player_id": "ranger_lyra",
                    "name": "Lyra",
                    "chips": 100,
                    "game_type": "darts",
                }
            )
            # Both clients receive Lyra's join
            ws_kip.receive_json()
            ws_lyra.receive_json()

            # Kip places wager
            ws_kip.send_json(
                {"action": "bet", "player_id": "archer_kip", "amount": 10, "bet_type": "dart_wager"}
            )
            b_kip1, b_kip2 = ws_kip.receive_json(), ws_lyra.receive_json()
            assert b_kip1["type"] == "bet_placed" and b_kip2["type"] == "bet_placed"
            assert b_kip1["pot"] == 10 and b_kip1["chips_remaining"] == 90

            # Kip throws dart with touch trajectory vector (vx=0, vy=0 -> Double Bullseye)
            ws_kip.send_json(
                {"action": "throw_dart", "player_id": "archer_kip", "vx": 0.0, "vy": 0.0}
            )
            t1_kip, t1_lyra = ws_kip.receive_json(), ws_lyra.receive_json()
            assert t1_kip["type"] == "dart_thrown" and t1_lyra["type"] == "dart_thrown"
            assert t1_kip["hit"]["points"] == 50
            assert t1_kip["score_remaining"] == 451
            assert t1_kip["next_turn"] == "ranger_lyra"

            # Lyra takes turn with touch trajectory vector
            ws_lyra.send_json(
                {"action": "throw_dart", "player_id": "ranger_lyra", "vx": 0.0, "vy": 7.0}
            )
            t2_kip, t2_lyra = ws_kip.receive_json(), ws_lyra.receive_json()
            assert t2_kip["type"] == "dart_thrown" and t2_lyra["type"] == "dart_thrown"
            assert t2_lyra["player_id"] == "ranger_lyra"
            assert t2_lyra["next_turn"] == "archer_kip"

    # ---------------- 2. Billiards Touch Trajectory Vector Exchange ----------------
    billiards_table_id = f"table-billiards-{uuid4().hex[:6]}"
    with (
        TestClient(session_app) as client_billiards,
        client_billiards.websocket_connect(f"/ws/minigames/{billiards_table_id}") as ws1,
    ):
        assert ws1.receive_json()["type"] == "connected"
        with client_billiards.websocket_connect(f"/ws/minigames/{billiards_table_id}") as ws2:
            assert ws2.receive_json()["type"] == "connected"

            ws1.send_json(
                {
                    "action": "join",
                    "player_id": "archer_kip",
                    "name": "Kip",
                    "chips": 100,
                    "game_type": "billiards",
                }
            )
            ws1.receive_json()
            ws2.receive_json()

            ws2.send_json(
                {
                    "action": "join",
                    "player_id": "ranger_lyra",
                    "name": "Lyra",
                    "chips": 100,
                    "game_type": "billiards",
                }
            )
            ws1.receive_json()
            ws2.receive_json()

            # Player 1 broadcasts cue ball stroke with touch trajectory vector
            shot1 = {
                "action": "billiards_stroke",
                "player_id": "archer_kip",
                "angle_deg": 45.0,
                "force": 75.0,
                "cue_vector": {"vx": 12.5, "vy": 12.5},
                "spin": "topspin",
                "target_ball": 8,
            }
            ws1.send_json(shot1)
            frame1_ws1, frame1_ws2 = ws1.receive_json(), ws2.receive_json()
            assert frame1_ws1["action"] == "billiards_stroke"
            assert frame1_ws2["cue_vector"] == {"vx": 12.5, "vy": 12.5}
            assert frame1_ws2["force"] == 75.0 and frame1_ws2["target_ball"] == 8

            # Player 2 responds with touch trajectory vector
            shot2 = {
                "action": "billiards_stroke",
                "player_id": "ranger_lyra",
                "angle_deg": 135.0,
                "force": 50.0,
                "cue_vector": {"vx": -8.0, "vy": 8.0},
                "spin": "draw",
                "target_ball": 3,
            }
            ws2.send_json(shot2)
            frame2_ws1, frame2_ws2 = ws1.receive_json(), ws2.receive_json()
            assert frame2_ws1["player_id"] == "ranger_lyra"
            assert frame2_ws2["cue_vector"] == {"vx": -8.0, "vy": 8.0}
            assert frame2_ws2["spin"] == "draw"


def test_casino_craps_and_roulette_betting_and_payouts(
    spicedb: MockSpiceDBClient, mock_bus: MockAsyncRedis
) -> None:
    """Wager placement, dice tumble resolution, and character coin purse crediting."""
    # ---------------- 1. Dragon Craps Wagering, Tumble, and Payouts ----------------
    craps_table_id = f"table-craps-{uuid4().hex[:6]}"
    with (
        TestClient(session_app) as client_craps,
        client_craps.websocket_connect(f"/ws/minigames/{craps_table_id}") as ws_craps,
    ):
        ws_craps.receive_json()
        # Gideon joins with 200 chips in coin purse
        ws_craps.send_json(
            {
                "action": "join",
                "player_id": "gambler_gideon",
                "name": "Gideon",
                "chips": 200,
                "game_type": "craps",
            }
        )
        ws_craps.receive_json()

        # Place pass_line (50) and field (25) wagers: purse reduced from 200 to 125
        ws_craps.send_json(
            {"action": "bet", "player_id": "gambler_gideon", "amount": 50, "bet_type": "pass_line"}
        )
        b1 = ws_craps.receive_json()
        assert b1["chips_remaining"] == 150

        ws_craps.send_json(
            {"action": "bet", "player_id": "gambler_gideon", "amount": 25, "bet_type": "field"}
        )
        b2 = ws_craps.receive_json()
        assert b2["chips_remaining"] == 125

        # Tumble dice: Natural 7 come-out roll -> pass line wins 100 chips, field loses
        ws_craps.send_json({"action": "roll_craps", "dice": [4, 3]})
        roll1 = ws_craps.receive_json()
        assert roll1["type"] == "craps_rolled" and roll1["total"] == 7
        assert "Natural 7" in roll1["narrative"]
        assert roll1["payouts"]["gambler_gideon"] == 100
        # Character coin purse credited: 125 + 100 = 225 chips
        assert roll1["player_balances"]["gambler_gideon"] == 225

        # Point Phase: Bet 50 pass_line (balance 175). Roll 6 establishes point
        ws_craps.send_json(
            {"action": "bet", "player_id": "gambler_gideon", "amount": 50, "bet_type": "pass_line"}
        )
        ws_craps.receive_json()
        ws_craps.send_json({"action": "roll_craps", "dice": [2, 4]})
        roll2 = ws_craps.receive_json()
        assert roll2["point"] == 6

        # Bet 25 field (balance 150). Roll 6 hits the point -> pass line pays 100 chips
        ws_craps.send_json(
            {"action": "bet", "player_id": "gambler_gideon", "amount": 25, "bet_type": "field"}
        )
        ws_craps.receive_json()
        ws_craps.send_json({"action": "roll_craps", "dice": [3, 3]})
        roll3 = ws_craps.receive_json()
        assert "Hit the point 6" in roll3["narrative"]
        assert roll3["payouts"]["gambler_gideon"] == 100
        # Character coin purse credited: 150 + 100 = 250 chips
        assert roll3["player_balances"]["gambler_gideon"] == 250

    # ---------------- 2. Roulette Multi-Patron Wagering and Payouts ----------------
    roulette_table_id = f"table-roulette-{uuid4().hex[:6]}"
    with (
        TestClient(session_app) as client_roulette,
        client_roulette.websocket_connect(f"/ws/minigames/{roulette_table_id}") as ws1,
    ):
        assert ws1.receive_json()["type"] == "connected"
        with client_roulette.websocket_connect(f"/ws/minigames/{roulette_table_id}") as ws2:
            assert ws2.receive_json()["type"] == "connected"

            ws1.send_json(
                {
                    "action": "join",
                    "player_id": "gambler_gideon",
                    "name": "Gideon",
                    "chips": 200,
                    "game_type": "roulette",
                }
            )
            ws1.receive_json()
            ws2.receive_json()

            ws2.send_json(
                {
                    "action": "join",
                    "player_id": "selene_highroller",
                    "name": "Selene",
                    "chips": 500,
                    "game_type": "roulette",
                }
            )
            ws1.receive_json()
            ws2.receive_json()

            # Gideon bets 50 on "red" (coin purse 150)
            ws1.send_json(
                {
                    "action": "bet",
                    "player_id": "gambler_gideon",
                    "amount": 50,
                    "bet_type": "color",
                    "target": "red",
                }
            )
            ws1.receive_json()
            ws2.receive_json()

            # Selene bets 20 on straight 14 (coin purse 480)
            ws2.send_json(
                {
                    "action": "bet",
                    "player_id": "selene_highroller",
                    "amount": 20,
                    "bet_type": "straight",
                    "target": 14,
                }
            )
            ws1.receive_json()
            ws2.receive_json()

            # Spin roulette: 14 is red -> Gideon gets 2x (100 chips), Selene gets 36x (720 chips)
            ws1.send_json({"action": "spin_roulette", "winning_number": 14})
            spin_res1, spin_res2 = ws1.receive_json(), ws2.receive_json()
            assert spin_res1["winning_number"] == 14 and spin_res1["color"] == "red"
            assert spin_res1["payouts"]["gambler_gideon"] == 100
            assert spin_res1["payouts"]["selene_highroller"] == 720
            # Character coin purses credited
            assert spin_res1["player_balances"]["gambler_gideon"] == 250
            assert spin_res1["player_balances"]["selene_highroller"] == 1200
            assert spin_res2["player_balances"] == spin_res1["player_balances"]
