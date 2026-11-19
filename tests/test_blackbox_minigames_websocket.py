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
from game_session.main import app as session_app
from runefoble_auth.mock import MockSpiceDBClient

from tests.helpers.minigame_tables import open_minigame_table
from tests.helpers.mock_redis import MockAsyncRedis
from tests.helpers.ws_identity import SIGNING_ISSUER, ws_subprotocols

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")

RED = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}


@pytest.fixture(autouse=True)
def default_table_patron(spicedb: MockSpiceDBClient) -> None:
    """The default table route checks est-default like any establishment. Grant the tester a patron seat."""
    asyncio.run(
        spicedb.write_relationship(
            "establishment", "est-default", "patron", "user", "minigame-tester"
        )
    )


@pytest.fixture(autouse=True)
def clean_minigame_state():
    from game_session.minigame_tables.ws_manager import minigame_table_manager

    minigame_table_manager.clear()
    yield
    minigame_table_manager.clear()


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

    open_minigame_table(
        darts_table_id, establishment_id=est_id, game_type="darts", user_id="archer_kip"
    )
    with (
        TestClient(
            session_app, headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint('test-user')}"}
        ) as client_darts,
        client_darts.websocket_connect(
            f"/ws/establishments/{est_id}/tables/{darts_table_id}",
            subprotocols=ws_subprotocols("archer_kip"),
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
            f"/ws/establishments/{est_id}/tables/{darts_table_id}",
            subprotocols=ws_subprotocols("ranger_lyra"),
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
    open_minigame_table(billiards_table_id, game_type="billiards")
    with (
        TestClient(
            session_app, headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint('test-user')}"}
        ) as client_billiards,
        client_billiards.websocket_connect(
            f"/ws/minigames/{billiards_table_id}", subprotocols=ws_subprotocols("minigame-tester")
        ) as ws1,
    ):
        assert ws1.receive_json()["type"] == "connected"
        with client_billiards.websocket_connect(
            f"/ws/minigames/{billiards_table_id}", subprotocols=ws_subprotocols("minigame-tester")
        ) as ws2:
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


def _grant_patron(spicedb: MockSpiceDBClient, *user_ids: str) -> None:
    for user_id in user_ids:
        asyncio.run(
            spicedb.write_relationship("establishment", "est-default", "patron", "user", user_id)
        )


def test_craps_roll_is_made_by_the_server_for_the_verified_player(
    spicedb: MockSpiceDBClient, mock_bus: MockAsyncRedis
) -> None:
    """The server rolls the dice and credits the principal. A forged player id and dice are ignored."""
    _grant_patron(spicedb, "gambler_gideon")
    table_id = f"table-craps-{uuid4().hex[:6]}"
    open_minigame_table(table_id, game_type="craps")
    with (
        TestClient(session_app) as client,
        client.websocket_connect(
            f"/ws/minigames/{table_id}", subprotocols=ws_subprotocols("gambler_gideon")
        ) as ws,
    ):
        ws.receive_json()
        ws.send_json({"action": "join", "player_id": "forged", "name": "Gideon", "chips": 200})
        assert ws.receive_json()["player_id"] == "gambler_gideon"

        ws.send_json(
            {"action": "bet", "player_id": "forged", "amount": 50, "bet_type": "pass_line"}
        )
        assert ws.receive_json()["chips_remaining"] == 150
        ws.send_json({"action": "bet", "amount": 25, "bet_type": "field"})
        assert ws.receive_json()["chips_remaining"] == 125

        # The client asks for 9 + 9. The server rolls its own dice.
        ws.send_json({"action": "roll_craps", "dice": [9, 9]})
        roll = ws.receive_json()
        assert roll["type"] == "craps_rolled"
        assert all(1 <= die <= 6 for die in roll["dice"])
        assert roll["total"] == sum(roll["dice"])
        paid = roll["payouts"].get("gambler_gideon", 0)
        assert roll["player_balances"] == {"gambler_gideon": 125 + paid}


def test_roulette_spin_is_made_by_the_server_for_the_verified_players(
    spicedb: MockSpiceDBClient, mock_bus: MockAsyncRedis
) -> None:
    """The server picks the winning number. Payouts follow it, and balances follow the payouts."""
    _grant_patron(spicedb, "gambler_gideon", "selene_highroller")
    table_id = f"table-roulette-{uuid4().hex[:6]}"
    open_minigame_table(table_id, game_type="roulette")
    with (
        TestClient(session_app) as client,
        client.websocket_connect(
            f"/ws/minigames/{table_id}", subprotocols=ws_subprotocols("gambler_gideon")
        ) as ws1,
        client.websocket_connect(
            f"/ws/minigames/{table_id}", subprotocols=ws_subprotocols("selene_highroller")
        ) as ws2,
    ):
        assert ws1.receive_json()["type"] == "connected"
        assert ws2.receive_json()["type"] == "connected"

        ws1.send_json({"action": "join", "name": "Gideon", "chips": 200})
        ws1.receive_json(), ws2.receive_json()
        ws2.send_json({"action": "join", "name": "Selene", "chips": 500})
        ws1.receive_json(), ws2.receive_json()

        ws1.send_json({"action": "bet", "amount": 50, "bet_type": "color", "target": "red"})
        ws1.receive_json(), ws2.receive_json()
        ws2.send_json({"action": "bet", "amount": 20, "bet_type": "straight", "target": 14})
        ws1.receive_json(), ws2.receive_json()

        # 99 is not a wheel number. The server ignores the client number and spins its own.
        ws1.send_json({"action": "spin_roulette", "winning_number": 99})
        spin1, spin2 = ws1.receive_json(), ws2.receive_json()
        assert spin1["type"] == "wheel_spun"
        number = spin1["winning_number"]
        assert 0 <= number <= 36
        assert spin1["color"] == ("green" if number == 0 else "red" if number in RED else "black")
        assert spin1["payouts"].get("gambler_gideon", 0) == (100 if spin1["color"] == "red" else 0)
        assert spin1["payouts"].get("selene_highroller", 0) == (720 if number == 14 else 0)
        assert spin1["player_balances"]["gambler_gideon"] == 150 + spin1["payouts"].get(
            "gambler_gideon", 0
        )
        assert spin1["player_balances"]["selene_highroller"] == 480 + spin1["payouts"].get(
            "selene_highroller", 0
        )
        assert spin2["player_balances"] == spin1["player_balances"]
