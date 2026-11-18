"""Frontdoor blackbox tests for mobile-first touch tavern and casino minigames suite.

TASK-0261 / PRD-0024 / US-0074 / ADR-0004 / ADR-0006 / ADR-0012
Governed by Hard Invariant 1 (SpiceDB Zanzibar auth), Hard Invariant 2 (eventsource events),
Hard Invariant 6 (<500 lines limit), and Hard Invariant 7 (Blackbox TDD).
"""

from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from game_session.events import STREAM_TAVERN
from game_session.main import app as session_app
from gateway_api.main import app as gateway_app
from runefoble_auth.spicedb import MockSpiceDBClient

from tests.helpers.minigame_tables import open_minigame_table
from tests.helpers.mock_redis import MockAsyncRedis
from tests.helpers.ws_identity import SIGNING_ISSUER, ws_subprotocols

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")


@pytest.fixture(autouse=True)
def clean_minigame_state():
    from game_session.minigame_tables.ws_manager import minigame_table_manager

    minigame_table_manager.connections.clear()
    yield
    minigame_table_manager.connections.clear()


@pytest.fixture(autouse=True)
def default_table_patron(spicedb: MockSpiceDBClient) -> None:
    """The default table route checks est-default like any establishment. Grant the tester a patron seat."""
    asyncio.run(
        spicedb.write_relationship(
            "establishment", "est-default", "patron", "user", "minigame-tester"
        )
    )


@pytest.fixture
def session_client(spicedb: MockSpiceDBClient):
    with TestClient(
        session_app, headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint('test-user')}"}
    ) as client:
        yield client


@pytest.fixture
def gateway_client(spicedb: MockSpiceDBClient):
    with TestClient(gateway_app) as client:
        yield client


def test_minigames_suite_manifest_advertises_components(session_client: TestClient) -> None:
    """Verify microfrontend manifest advertises the minigames components."""
    res = session_client.get("/ui/manifest")
    assert res.status_code == 200
    manifest = res.json()
    assert "runefoble-minigame-darts" in manifest["components"]
    assert "runefoble-minigame-liars-dice" in manifest["components"]
    assert "runefoble-minigame-roulette" in manifest["components"]


def test_blackbox_darts_table_join_bet_and_throw(
    session_client: TestClient, spicedb: MockSpiceDBClient, mock_bus: MockAsyncRedis
) -> None:
    """Multiplayer darts table: joining, bet placement, flick throw, and score synchronization."""
    table_id = f"table-darts-{uuid4().hex[:6]}"
    establishment_id = "est-salty-siren"

    asyncio.run(
        spicedb.write_relationship("establishment", establishment_id, "patron", "user", "kip")
    )
    asyncio.run(
        spicedb.write_relationship("establishment", establishment_id, "patron", "user", "sam")
    )

    open_minigame_table(
        table_id, establishment_id=establishment_id, game_type="darts", user_id="kip"
    )

    with session_client.websocket_connect(
        f"/ws/establishments/{establishment_id}/tables/{table_id}",
        subprotocols=ws_subprotocols("kip"),
    ) as ws1:
        assert ws1.receive_json()["type"] == "connected"
        ws1.send_json(
            {
                "action": "join",
                "player_id": "kip",
                "name": "Kip the Nimble",
                "chips": 100,
                "game_type": "darts",
            }
        )
        assert ws1.receive_json()["type"] == "player_joined"

        with session_client.websocket_connect(
            f"/ws/establishments/{establishment_id}/tables/{table_id}",
            subprotocols=ws_subprotocols("sam"),
        ) as ws2:
            ws2.receive_json()
            ws2.send_json(
                {
                    "action": "join",
                    "player_id": "sam",
                    "name": "Sam Spectator",
                    "chips": 50,
                    "game_type": "darts",
                }
            )
            assert ws1.receive_json()["player_id"] == "sam"
            assert ws2.receive_json()["player_id"] == "sam"

            ws1.send_json(
                {"action": "bet", "player_id": "kip", "amount": 10, "bet_type": "dart_wager"}
            )
            bet_msg1, bet_msg2 = ws1.receive_json(), ws2.receive_json()
            assert bet_msg1["type"] == "bet_placed" and bet_msg2["type"] == "bet_placed"
            assert bet_msg1["pot"] == 10 and bet_msg1["chips_remaining"] == 90

            ws1.send_json({"action": "throw_dart", "player_id": "kip", "vx": 0.0, "vy": 0.0})
            t1, t2 = ws1.receive_json(), ws2.receive_json()
            assert t1["type"] == "dart_thrown" and t2["type"] == "dart_thrown"
            assert t1["hit"]["points"] == 50  # Double Bullseye
            assert t1["score_remaining"] == 451
            assert t1["next_turn"] == "sam"

    stream_events = mock_bus.streams.get(STREAM_TAVERN, [])
    assert len(stream_events) >= 2


def test_blackbox_roulette_multiplayer_bets_and_payouts(
    session_client: TestClient, mock_bus: MockAsyncRedis
) -> None:
    """Roulette table: multiple betting tokens, wheel spin, and 35:1 / 1:1 payouts."""
    table_id = f"table-roulette-{uuid4().hex[:6]}"
    open_minigame_table(table_id, game_type="roulette")

    with session_client.websocket_connect(
        f"/ws/minigames/{table_id}", subprotocols=ws_subprotocols("minigame-tester")
    ) as ws1:
        assert ws1.receive_json()["type"] == "connected"
        with session_client.websocket_connect(
            f"/ws/minigames/{table_id}", subprotocols=ws_subprotocols("minigame-tester")
        ) as ws2:
            assert ws2.receive_json()["type"] == "connected"
            ws1.send_json(
                {
                    "action": "join",
                    "player_id": "player_black",
                    "name": "Black Bettor",
                    "chips": 100,
                }
            )
            ws1.receive_json(), ws2.receive_json()

            ws2.send_json(
                {
                    "action": "join",
                    "player_id": "player_straight",
                    "name": "Straight Bettor",
                    "chips": 100,
                }
            )
            ws1.receive_json(), ws2.receive_json()

            # Player 1 bets 20 on black; Player 2 bets 10 on straight 17 (which is black)
            ws1.send_json(
                {
                    "action": "bet",
                    "player_id": "player_black",
                    "amount": 20,
                    "bet_type": "color",
                    "target": "black",
                }
            )
            ws1.receive_json(), ws2.receive_json()

            ws2.send_json(
                {
                    "action": "bet",
                    "player_id": "player_straight",
                    "amount": 10,
                    "bet_type": "straight",
                    "target": 17,
                }
            )
            ws1.receive_json(), ws2.receive_json()

            ws1.send_json({"action": "spin_roulette", "winning_number": 17})
            res1, res2 = ws1.receive_json(), ws2.receive_json()
            assert res1["type"] == "wheel_spun" and res2["type"] == "wheel_spun"
            assert res1["winning_number"] == 17 and res1["color"] == "black"
            assert res1["payouts"]["player_black"] == 40
            assert res1["payouts"]["player_straight"] == 360
            assert res1["player_balances"]["player_black"] == 120
            assert res1["player_balances"]["player_straight"] == 450


def test_blackbox_liars_dice_turn_progression_and_challenge(
    session_client: TestClient, mock_bus: MockAsyncRedis
) -> None:
    """Liar's dice table: bid escalation, bluff challenge, and victory payout."""
    table_id = f"table-liars-{uuid4().hex[:6]}"
    open_minigame_table(table_id, game_type="liars_dice")

    with session_client.websocket_connect(
        f"/ws/minigames/{table_id}", subprotocols=ws_subprotocols("minigame-tester")
    ) as ws1:
        assert ws1.receive_json()["type"] == "connected"
        with session_client.websocket_connect(
            f"/ws/minigames/{table_id}", subprotocols=ws_subprotocols("minigame-tester")
        ) as ws2:
            assert ws2.receive_json()["type"] == "connected"
            ws1.send_json(
                {
                    "action": "join",
                    "player_id": "p1",
                    "name": "Cap'n Flint",
                    "chips": 50,
                    "game_type": "liars_dice",
                }
            )
            ws1.receive_json(), ws2.receive_json()

            ws2.send_json(
                {
                    "action": "join",
                    "player_id": "p2",
                    "name": "Silver",
                    "chips": 50,
                    "game_type": "liars_dice",
                }
            )
            ws1.receive_json(), ws2.receive_json()

            ws1.send_json({"action": "bet", "player_id": "p1", "amount": 25})
            ws1.receive_json(), ws2.receive_json()
            ws2.send_json({"action": "bet", "player_id": "p2", "amount": 25})
            ws1.receive_json(), ws2.receive_json()

            # P1 bids 2 threes
            ws1.send_json({"action": "bid", "player_id": "p1", "quantity": 2, "face": 3})
            b1, b2 = ws1.receive_json(), ws2.receive_json()
            assert b1["type"] == "bid_placed" and b2["type"] == "bid_placed"
            assert b1["bid"]["quantity"] == 2 and b1["bid"]["face"] == 3

            # P2 calls bluff
            ws2.send_json({"action": "challenge", "challenger_id": "p2"})
            c1, c2 = ws1.receive_json(), ws2.receive_json()
            assert c1["type"] == "challenge_resolved" and c2["type"] == "challenge_resolved"
            assert "matching_count" in c1 and c1["winner_id"] in ("p1", "p2")


def test_blackbox_dragon_craps_pass_line_and_field_roll(session_client: TestClient) -> None:
    """Dragon Craps: Come-out natural 7 win and field bets."""
    table_id = f"table-craps-{uuid4().hex[:6]}"
    open_minigame_table(table_id, game_type="craps")

    with session_client.websocket_connect(
        f"/ws/minigames/{table_id}", subprotocols=ws_subprotocols("minigame-tester")
    ) as ws:
        ws.receive_json()
        ws.send_json(
            {
                "action": "join",
                "player_id": "shooter_kip",
                "name": "Shooter Kip",
                "chips": 100,
                "game_type": "craps",
            }
        )
        ws.receive_json()

        ws.send_json(
            {"action": "bet", "player_id": "shooter_kip", "amount": 10, "bet_type": "pass_line"}
        )
        ws.receive_json()
        ws.send_json(
            {"action": "bet", "player_id": "shooter_kip", "amount": 10, "bet_type": "field"}
        )
        ws.receive_json()

        ws.send_json({"action": "roll_craps", "dice": [3, 4]})
        roll_res = ws.receive_json()
        assert roll_res["type"] == "craps_rolled" and roll_res["total"] == 7
        assert "Natural 7" in roll_res["narrative"]
        assert roll_res["payouts"]["shooter_kip"] == 20
        assert roll_res["player_balances"]["shooter_kip"] == 100


def test_blackbox_zanzibar_establishment_authorization(
    session_client: TestClient, spicedb: MockSpiceDBClient
) -> None:
    """SpiceDB Zanzibar: verify unauthorized patrons are rejected with 4003."""
    asyncio.run(
        spicedb.write_relationship("establishment", "est-vip-lounge", "patron", "user", "vip_kip")
    )

    with session_client.websocket_connect(
        "/ws/establishments/est-vip-lounge/tables/tbl-1",
        subprotocols=ws_subprotocols("stranger_user"),
    ) as ws_unauth:
        err_msg = ws_unauth.receive_json()
        assert err_msg["type"] == "error"
        assert err_msg["code"] == "PERMISSION_DENIED"

    open_minigame_table("tbl-1", establishment_id="est-vip-lounge", user_id="vip_kip")

    with session_client.websocket_connect(
        "/ws/establishments/est-vip-lounge/tables/tbl-1", subprotocols=ws_subprotocols("vip_kip")
    ) as ws_auth:
        assert ws_auth.receive_json()["type"] == "connected"


def test_blackbox_gateway_minigames_websocket_proxy(gateway_client: TestClient) -> None:
    """Gateway API: verify gateway routes minigames WebSocket tables."""
    table_id = f"table-gw-{uuid4().hex[:6]}"
    open_minigame_table(table_id, game_type="darts")
    with gateway_client.websocket_connect(
        f"/ws/minigames/{table_id}", subprotocols=ws_subprotocols("minigame-tester")
    ) as ws:
        msg = ws.receive_json()
        assert msg["type"] == "connected" and msg["table_id"] == table_id
