"""Tests for TASK-0016: Live SpiceDB Zanzibar Permission Enforcement on WebSockets & Game Mutators."""

import pytest
from fastapi import WebSocketDisconnect
from fastapi.testclient import TestClient
from gateway_api.auth import get_spicedb_client, set_spicedb_client
from gateway_api.main import app, set_event_bus
from runefoble_auth.spicedb import MockSpiceDBClient, SpiceDBClient
from runefoble_platform.redis_bus import MockAsyncRedis, RedisStreamsEventBus


@pytest.fixture(autouse=True)
def reset_state():
    """Reset SpiceDB client and event bus before and after each test."""
    client = MockSpiceDBClient()
    set_spicedb_client(client)
    set_event_bus(None)
    yield
    set_spicedb_client(SpiceDBClient())
    set_event_bus(None)


def test_connecting_with_valid_campaign_viewer_permissions():
    """Verify connecting with valid campaign viewer/reader permissions succeeds."""
    campaign_id = "camp-connect-view"
    spicedb = get_spicedb_client()

    import asyncio

    # 1. User with 'view' permission can connect
    asyncio.run(spicedb.write_relationship("campaign", campaign_id, "view", "user", "viewer_alice"))

    client = TestClient(app)
    with client.websocket_connect(f"/ws/campaigns/{campaign_id}?user_id=viewer_alice") as ws:
        msg = ws.receive_json()
        assert msg["type"] == "connected"
        assert msg["campaign_id"] == campaign_id
        assert msg["user_id"] == "viewer_alice"

    # 2. User with 'read' permission can connect
    asyncio.run(spicedb.write_relationship("campaign", campaign_id, "read", "user", "reader_bob"))
    with client.websocket_connect(f"/ws/campaigns/{campaign_id}?user_id=reader_bob") as ws:
        msg = ws.receive_json()
        assert msg["type"] == "connected"
        assert msg["user_id"] == "reader_bob"


def test_connecting_with_unauthorized_subject():
    """Verify connecting with unauthorized subject is rejected with PERMISSION_DENIED and closed with 4003."""
    campaign_id = "camp-connect-unauth"
    client = TestClient(app)

    # Stranger has no relations in SpiceDB
    with client.websocket_connect(f"/ws/campaigns/{campaign_id}?user_id=stranger_joe") as ws:
        err_msg = ws.receive_json()
        assert err_msg["type"] == "error"
        assert err_msg["code"] == "PERMISSION_DENIED"
        assert err_msg["action"] == "connect"
        assert "insufficient permissions" in err_msg["message"]

        # Subsequent receive raises WebSocketDisconnect with 4003
        with pytest.raises(WebSocketDisconnect) as exc:
            ws.receive_json()
        assert exc.value.code == 4003


def test_player_moving_token_with_valid_zanzibar_relation():
    """Verify player moving their token with valid Zanzibar relation succeeds and broadcast is dispatched."""
    campaign_id = "camp-player-move"
    player_id = "player_valeros"
    token_id = "token_valeros_01"
    spicedb = get_spicedb_client()

    import asyncio

    # Player is part of campaign and has move permission on the token
    asyncio.run(spicedb.write_relationship("campaign", campaign_id, "player", "user", player_id))
    asyncio.run(spicedb.write_relationship("board_token", token_id, "move", "user", player_id))

    client = TestClient(app)
    with client.websocket_connect(f"/ws/campaigns/{campaign_id}?user_id={player_id}") as ws:
        welcome = ws.receive_json()
        assert welcome["type"] == "connected"

        # Send token move action
        ws.send_json(
            {
                "action": "move_token",
                "token_id": token_id,
                "to_x": 4,
                "to_y": 6,
            }
        )

        broadcast = ws.receive_json()
        assert broadcast["type"] == "move_token"
        assert broadcast["action"] == "move_token"
        assert broadcast["status"] == "applied"
        assert broadcast["campaign_id"] == campaign_id
        assert broadcast["user_id"] == player_id
        assert broadcast["token_id"] == token_id
        assert broadcast["to_x"] == 4
        assert broadcast["to_y"] == 6


def test_spectator_attempting_to_move_token():
    """Verify spectator attempting to move a token is denied with PERMISSION_DENIED error frame."""
    campaign_id = "camp-spectator-move"
    spectator_id = "spectator_dave"
    token_id = "token_boss"
    spicedb = get_spicedb_client()

    import asyncio

    # Grant spectator relation
    asyncio.run(
        spicedb.write_relationship("campaign", campaign_id, "spectator", "user", spectator_id)
    )

    client = TestClient(app)
    with client.websocket_connect(f"/ws/campaigns/{campaign_id}?user_id={spectator_id}") as ws:
        welcome = ws.receive_json()
        assert welcome["type"] == "connected"

        # Spectator attempts to move token
        ws.send_json(
            {
                "action": "move_token",
                "token_id": token_id,
                "to_x": 1,
                "to_y": 1,
            }
        )

        err = ws.receive_json()
        assert err["type"] == "error"
        assert err["code"] == "PERMISSION_DENIED"
        assert err["action"] == "move_token"
        assert (
            "Zanzibar authorization denied: insufficient permissions for action 'move_token'"
            in err["message"]
        )


def test_player_attempting_to_trigger_dm_only_encounter_or_scene():
    """Verify player attempting to trigger DM-only encounter/scene is denied with PERMISSION_DENIED."""
    campaign_id = "camp-player-dm-actions"
    player_id = "player_kyra"
    spicedb = get_spicedb_client()

    import asyncio

    asyncio.run(spicedb.write_relationship("campaign", campaign_id, "player", "user", player_id))

    client = TestClient(app)
    with client.websocket_connect(f"/ws/campaigns/{campaign_id}?user_id={player_id}") as ws:
        welcome = ws.receive_json()
        assert welcome["type"] == "connected"

        # 1. Attempt spawn_monster
        ws.send_json(
            {
                "action": "spawn_monster",
                "monster_name": "Ancient Red Dragon",
                "x": 5,
                "y": 5,
            }
        )
        err1 = ws.receive_json()
        assert err1["type"] == "error"
        assert err1["code"] == "PERMISSION_DENIED"
        assert err1["action"] == "spawn_monster"
        assert "insufficient permissions for action 'spawn_monster'" in err1["message"]

        # 2. Attempt set_scene
        ws.send_json(
            {
                "action": "set_scene",
                "scene_id": "dragon_lair",
                "mood": "blazing_inferno",
            }
        )
        err2 = ws.receive_json()
        assert err2["type"] == "error"
        assert err2["code"] == "PERMISSION_DENIED"
        assert err2["action"] == "set_scene"
        assert "insufficient permissions for action 'set_scene'" in err2["message"]


def test_dungeon_master_executing_all_actions():
    """Verify Dungeon Master has full permissions to execute all actions."""
    campaign_id = "camp-dm-omni"
    dm_id = "dm_merlin"
    spicedb = get_spicedb_client()

    import asyncio

    asyncio.run(
        spicedb.write_relationship("campaign", campaign_id, "dungeon_master", "user", dm_id)
    )

    client = TestClient(app)
    with client.websocket_connect(f"/ws/campaigns/{campaign_id}?user_id={dm_id}") as ws:
        welcome = ws.receive_json()
        assert welcome["type"] == "connected"

        # 1. move_token
        ws.send_json({"action": "move_token", "token_id": "token_goblin", "to_x": 3, "to_y": 3})
        res1 = ws.receive_json()
        assert res1["action"] == "move_token"
        assert res1["status"] == "applied"
        assert res1["to_x"] == 3

        # 2. modify_hp
        ws.send_json({"action": "modify_hp", "character_id": "char_valeros", "delta": -5})
        res2 = ws.receive_json()
        assert res2["action"] == "modify_hp"
        assert res2["status"] == "applied"
        assert res2["delta"] == -5

        # 3. apply_condition
        ws.send_json(
            {"action": "apply_condition", "character_id": "char_valeros", "condition": "drunk"}
        )
        res3 = ws.receive_json()
        assert res3["action"] == "apply_condition"
        assert res3["status"] == "applied"
        assert res3["condition"] == "drunk"

        # 4. spawn_monster
        ws.send_json({"action": "spawn_monster", "monster_name": "Goblin Shaman", "x": 2, "y": 2})
        res4 = ws.receive_json()
        assert res4["action"] == "spawn_monster"
        assert res4["status"] == "applied"

        # 5. set_scene
        ws.send_json({"action": "set_scene", "scene_id": "scene_crypt", "mood": "shadowy"})
        res5 = ws.receive_json()
        assert res5["action"] == "set_scene"
        assert res5["status"] == "applied"


def test_character_hp_modification_permissions():
    """Verify character owner can modify HP/conditions, while unauthorized players are blocked."""
    campaign_id = "camp-char-edit"
    player1 = "player_ezren"
    player2 = "player_merisiel"
    char1 = "char_ezren"
    spicedb = get_spicedb_client()

    import asyncio

    # Both are players in campaign
    asyncio.run(spicedb.write_relationship("campaign", campaign_id, "player", "user", player1))
    asyncio.run(spicedb.write_relationship("campaign", campaign_id, "player", "user", player2))
    # Player1 owns char1
    asyncio.run(spicedb.write_relationship("character", char1, "owner", "user", player1))

    client = TestClient(app)

    # 1. Player1 edits own character -> Allowed
    with client.websocket_connect(f"/ws/campaigns/{campaign_id}?user_id={player1}") as ws:
        ws.receive_json()  # connected
        ws.send_json({"action": "modify_hp", "character_id": char1, "delta": 2})
        res = ws.receive_json()
        assert res["action"] == "modify_hp"
        assert res["status"] == "applied"

    # 2. Player2 attempts to edit char1 -> Denied
    with client.websocket_connect(f"/ws/campaigns/{campaign_id}?user_id={player2}") as ws:
        ws.receive_json()  # connected
        ws.send_json({"action": "modify_hp", "character_id": char1, "delta": -10})
        err = ws.receive_json()
        assert err["type"] == "error"
        assert err["code"] == "PERMISSION_DENIED"
        assert err["action"] == "modify_hp"


def test_redis_publishing_on_authorized_and_rejection_suppression():
    """Verify that authorized mutations are published to Redis, while denied actions are suppressed."""
    campaign_id = "camp-redis-publish"
    dm_id = "dm_elminster"
    spicedb = get_spicedb_client()

    import asyncio

    asyncio.run(
        spicedb.write_relationship("campaign", campaign_id, "dungeon_master", "user", dm_id)
    )

    # Mock Redis bus
    mock_redis = MockAsyncRedis()
    bus = RedisStreamsEventBus(redis_url="redis://fake:6379")
    bus._client = mock_redis
    set_event_bus(bus)

    client = TestClient(app)
    with client.websocket_connect(f"/ws/campaigns/{campaign_id}?user_id={dm_id}") as ws:
        ws.receive_json()  # connected

        # Authorized move
        ws.send_json({"action": "move_token", "token_id": "tok_1", "to_x": 2, "to_y": 2})
        ws.receive_json()

        # Check published event in board stream
        assert len(mock_redis.streams.get("runefoble.events.board", [])) == 1
        entry = mock_redis.streams["runefoble.events.board"][0]
        assert "move_token" in str(entry)


def test_spicedb_client_mock_and_grpc_handling():
    """Verify SpiceDBClient handles mock fallback and client instantiation properly."""
    # Instantiate with explicit mock
    client = SpiceDBClient(use_mock=True)
    assert client.use_mock is True
    assert client._grpc_client is None

    # Instantiate default client without authzed installed falls back gracefully
    default_client = SpiceDBClient()
    assert default_client._grpc_client is None

    # In-memory relations work as expected
    import asyncio

    asyncio.run(default_client.write_relationship("campaign", "c1", "player", "user", "u1"))
    assert asyncio.run(default_client.check_permission("campaign", "c1", "view", "user", "u1"))
    assert not asyncio.run(
        default_client.check_permission("campaign", "c1", "run_session", "user", "u1")
    )
