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
from game_session.dependencies import set_event_bus, set_spicedb_client
from game_session.events import STREAM_TAVERN
from game_session.main import app as session_app
from gateway_api.main import app as gateway_app
from runefoble_auth.factory import get_spicedb_client
from runefoble_auth.spicedb import MockSpiceDBClient
from runefoble_platform.redis_bus import RedisStreamsEventBus

from tests.helpers.minigame_tables import open_minigame_table
from tests.helpers.mock_redis import MockAsyncRedis
from tests.helpers.ws_identity import SIGNING_ISSUER, ws_subprotocols

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")


@pytest.fixture
def mock_bus() -> MockAsyncRedis:
    redis_client = MockAsyncRedis()
    bus = RedisStreamsEventBus(client=redis_client)
    set_event_bus(bus)
    yield redis_client
    set_event_bus(None)


@pytest.fixture(autouse=True)
def clean_minigame_state():
    from game_session.minigame_tables.ws_manager import minigame_table_manager

    minigame_table_manager.connections.clear()
    yield
    minigame_table_manager.connections.clear()


@pytest.fixture
def spicedb() -> MockSpiceDBClient:
    mock_db = get_spicedb_client()
    set_spicedb_client(mock_db)
    yield mock_db
    set_spicedb_client(MockSpiceDBClient())


@pytest.fixture(autouse=True)
def default_table_patron(spicedb: MockSpiceDBClient) -> None:
    """The default table route checks est-default like any establishment. Grant the testers a patron seat."""
    for user_id in (
        "minigame-tester",
        "player_black",
        "player_straight",
        "p1",
        "p2",
        "shooter_kip",
    ):
        asyncio.run(
            spicedb.write_relationship("establishment", "est-default", "patron", "user", user_id)
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
    """Roulette table: each socket acts as its principal, and the server picks the winning number."""
    table_id = f"table-roulette-{uuid4().hex[:6]}"
    open_minigame_table(table_id, game_type="roulette")
    path = f"/ws/minigames/{table_id}"

    with (
        session_client.websocket_connect(path, subprotocols=ws_subprotocols("player_black")) as ws1,
        session_client.websocket_connect(
            path, subprotocols=ws_subprotocols("player_straight")
        ) as ws2,
    ):
        assert ws1.receive_json()["type"] == "connected"
        assert ws2.receive_json()["type"] == "connected"
        ws1.send_json({"action": "join", "name": "Black Bettor", "chips": 100})
        ws1.receive_json(), ws2.receive_json()
        ws2.send_json({"action": "join", "name": "Straight Bettor", "chips": 100})
        ws1.receive_json(), ws2.receive_json()

        # A forged player id in the message does not move the bet to another seat.
        ws1.send_json(
            {
                "action": "bet",
                "player_id": "player_straight",
                "amount": 20,
                "bet_type": "color",
                "target": "black",
            }
        )
        bet1, _ = ws1.receive_json(), ws2.receive_json()
        assert bet1["player_id"] == "player_black"
        ws2.send_json({"action": "bet", "amount": 10, "bet_type": "straight", "target": 17})
        ws1.receive_json(), ws2.receive_json()

        ws1.send_json({"action": "spin_roulette", "winning_number": 17})
        res1, res2 = ws1.receive_json(), ws2.receive_json()
        assert res1["type"] == "wheel_spun" and res2["type"] == "wheel_spun"
        number = res1["winning_number"]
        assert 0 <= number <= 36
        black = res1["color"] == "black"
        assert res1["payouts"].get("player_black", 0) == (40 if black else 0)
        assert res1["payouts"].get("player_straight", 0) == (360 if number == 17 else 0)
        assert res1["player_balances"]["player_black"] == 80 + res1["payouts"].get(
            "player_black", 0
        )
        assert res1["player_balances"]["player_straight"] == 90 + res1["payouts"].get(
            "player_straight", 0
        )


def test_blackbox_liars_dice_turn_progression_and_challenge(
    session_client: TestClient, mock_bus: MockAsyncRedis
) -> None:
    """Liar's dice table: bid escalation and bluff challenge, each as the verified player."""
    table_id = f"table-liars-{uuid4().hex[:6]}"
    open_minigame_table(table_id, game_type="liars_dice")
    path = f"/ws/minigames/{table_id}"

    with (
        session_client.websocket_connect(path, subprotocols=ws_subprotocols("p1")) as ws1,
        session_client.websocket_connect(path, subprotocols=ws_subprotocols("p2")) as ws2,
    ):
        assert ws1.receive_json()["type"] == "connected"
        assert ws2.receive_json()["type"] == "connected"
        ws1.send_json({"action": "join", "name": "Cap'n Flint", "chips": 50})
        ws1.receive_json(), ws2.receive_json()
        ws2.send_json({"action": "join", "name": "Silver", "chips": 50})
        ws1.receive_json(), ws2.receive_json()

        ws1.send_json({"action": "bet", "amount": 25})
        ws1.receive_json(), ws2.receive_json()
        ws2.send_json({"action": "bet", "amount": 25})
        ws1.receive_json(), ws2.receive_json()

        ws1.send_json({"action": "bid", "quantity": 2, "face": 3})
        b1, b2 = ws1.receive_json(), ws2.receive_json()
        assert b1["type"] == "bid_placed" and b2["type"] == "bid_placed"
        assert b1["bid"]["quantity"] == 2 and b1["bid"]["face"] == 3

        # p1 names p2 as the challenger. The server uses the socket principal, p2.
        ws2.send_json({"action": "challenge", "challenger_id": "p1"})
        c1, c2 = ws1.receive_json(), ws2.receive_json()
        assert c1["type"] == "challenge_resolved" and c2["type"] == "challenge_resolved"
        assert "matching_count" in c1 and c1["winner_id"] in ("p1", "p2")


def test_blackbox_dragon_craps_pass_line_and_field_roll(session_client: TestClient) -> None:
    """Dragon Craps: Come-out natural 7 win and field bets."""
    table_id = f"table-craps-{uuid4().hex[:6]}"
    open_minigame_table(table_id, game_type="craps")

    with session_client.websocket_connect(
        f"/ws/minigames/{table_id}", subprotocols=ws_subprotocols("shooter_kip")
    ) as ws:
        ws.receive_json()
        ws.send_json({"action": "join", "name": "Shooter Kip", "chips": 100, "game_type": "craps"})
        ws.receive_json()

        ws.send_json(
            {"action": "bet", "player_id": "shooter_kip", "amount": 10, "bet_type": "pass_line"}
        )
        ws.receive_json()
        ws.send_json(
            {"action": "bet", "player_id": "shooter_kip", "amount": 10, "bet_type": "field"}
        )
        ws.receive_json()

        # The client asks for 9 + 9. The server rolls its own dice.
        ws.send_json({"action": "roll_craps", "dice": [9, 9]})
        roll_res = ws.receive_json()
        assert roll_res["type"] == "craps_rolled"
        assert all(1 <= die <= 6 for die in roll_res["dice"])
        assert roll_res["total"] == sum(roll_res["dice"])
        paid = roll_res["payouts"].get("shooter_kip", 0)
        assert roll_res["player_balances"]["shooter_kip"] == 80 + paid


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
