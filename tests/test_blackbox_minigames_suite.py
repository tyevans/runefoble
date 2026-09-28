"""Frontdoor blackbox tests for mobile-first touch tavern and casino minigames suite.

TASK-0261 / PRD-0024 / US-0074 / ADR-0004 / ADR-0006 / ADR-0012
Governed by Hard Invariant 1 (SpiceDB Zanzibar auth), Hard Invariant 2 (eventsource events),
Hard Invariant 6 (<500 lines limit), and Hard Invariant 7 (Blackbox TDD).
"""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from game_session.dependencies import STREAM_TAVERN, set_event_bus, set_spicedb_client
from game_session.main import app as session_app
from gateway_api.auth import set_spicedb_client as set_gateway_spicedb
from gateway_api.main import app as gateway_app
from runefoble_auth.spicedb import MockSpiceDBClient
from runefoble_platform.mock_redis import MockAsyncRedis
from runefoble_platform.redis_bus import RedisStreamsEventBus

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def mock_bus() -> MockAsyncRedis:
    redis_client = MockAsyncRedis()
    bus = RedisStreamsEventBus(client=redis_client)
    set_event_bus(bus)
    yield redis_client
    set_event_bus(None)


@pytest.fixture
def spicedb() -> MockSpiceDBClient:
    mock_db = MockSpiceDBClient()
    set_spicedb_client(mock_db)
    set_gateway_spicedb(mock_db)
    yield mock_db
    set_spicedb_client(None)
    set_gateway_spicedb(None)


@pytest.fixture
def session_client(spicedb: MockSpiceDBClient) -> TestClient:
    return TestClient(session_app)


@pytest.fixture
def gateway_client(spicedb: MockSpiceDBClient) -> TestClient:
    return TestClient(gateway_app)


def test_minigames_suite_manifest_and_file_invariants(session_client: TestClient) -> None:
    """Verify microfrontend manifest advertises minigames components and files satisfy line limits."""
    res = session_client.get("/ui/manifest")
    assert res.status_code == 200
    manifest = res.json()
    assert "runefoble-minigame-darts" in manifest["components"]
    assert "runefoble-minigame-liars-dice" in manifest["components"]
    assert "runefoble-minigame-roulette" in manifest["components"]

    frontend_dir = REPO_ROOT / "frontend" / "src" / "components" / "minigames"
    darts_file = frontend_dir / "runefoble-minigame-darts.ts"
    liars_file = frontend_dir / "runefoble-minigame-liars-dice.ts"
    roulette_file = frontend_dir / "runefoble-minigame-roulette.ts"
    stories_file = REPO_ROOT / "frontend" / "src" / "stories" / "runefoble-minigames.stories.ts"

    assert darts_file.is_file() and liars_file.is_file() and roulette_file.is_file()
    assert stories_file.is_file()
    assert len(darts_file.read_text().splitlines()) < 300
    assert len(liars_file.read_text().splitlines()) < 280
    assert len(roulette_file.read_text().splitlines()) < 280


@pytest.mark.asyncio
async def test_blackbox_darts_table_join_bet_and_throw(
    session_client: TestClient, spicedb: MockSpiceDBClient, mock_bus: MockAsyncRedis
) -> None:
    """Multiplayer darts table: joining, bet placement, flick throw, and score synchronization."""
    table_id = f"table-darts-{uuid4().hex[:6]}"
    establishment_id = "est-salty-siren"

    await spicedb.write_relationship("establishment", establishment_id, "patron", "user", "kip")
    await spicedb.write_relationship("establishment", establishment_id, "patron", "user", "sam")

    with session_client.websocket_connect(
        f"/ws/establishments/{establishment_id}/tables/{table_id}?user_id=kip"
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
            f"/ws/establishments/{establishment_id}/tables/{table_id}?user_id=sam"
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

    with (
        session_client.websocket_connect(f"/ws/minigames/{table_id}") as ws1,
        session_client.websocket_connect(f"/ws/minigames/{table_id}") as ws2,
    ):
        ws1.receive_json(), ws2.receive_json()
        ws1.send_json(
            {"action": "join", "player_id": "player_black", "name": "Black Bettor", "chips": 100}
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

    with (
        session_client.websocket_connect(f"/ws/minigames/{table_id}") as ws1,
        session_client.websocket_connect(f"/ws/minigames/{table_id}") as ws2,
    ):
        ws1.receive_json(), ws2.receive_json()
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

    with session_client.websocket_connect(f"/ws/minigames/{table_id}") as ws:
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


@pytest.mark.asyncio
async def test_blackbox_zanzibar_establishment_authorization(
    session_client: TestClient, spicedb: MockSpiceDBClient
) -> None:
    """SpiceDB Zanzibar: verify unauthorized patrons are rejected with 4003."""
    await spicedb.write_relationship("establishment", "est-vip-lounge", "patron", "user", "vip_kip")

    with session_client.websocket_connect(
        "/ws/establishments/est-vip-lounge/tables/tbl-1?user_id=stranger_user"
    ) as ws_unauth:
        err_msg = ws_unauth.receive_json()
        assert err_msg["type"] == "error"
        assert err_msg["code"] == "PERMISSION_DENIED"

    with session_client.websocket_connect(
        "/ws/establishments/est-vip-lounge/tables/tbl-1?user_id=vip_kip"
    ) as ws_auth:
        assert ws_auth.receive_json()["type"] == "connected"


def test_blackbox_gateway_minigames_websocket_proxy(gateway_client: TestClient) -> None:
    """Gateway API: verify gateway routes minigames WebSocket tables."""
    table_id = f"table-gw-{uuid4().hex[:6]}"
    with gateway_client.websocket_connect(f"/ws/minigames/{table_id}") as ws:
        msg = ws.receive_json()
        assert msg["type"] == "connected" and msg["table_id"] == table_id
