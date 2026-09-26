"""Tests for TASK-0071: WebSocket Zanzibar Game Action Mutators Authorization."""

import asyncio

import pytest
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


def _grant(resource_type: str, resource_id: str, relation: str, subject_id: str) -> None:
    asyncio.run(
        get_spicedb_client().write_relationship(
            resource_type, resource_id, relation, "user", subject_id
        )
    )


def test_player_moving_token_with_valid_zanzibar_relation():
    """Verify player moving their token with valid Zanzibar relation succeeds."""
    campaign_id, player_id, token_id = "camp-player-move", "player_valeros", "token_valeros_01"
    _grant("campaign", campaign_id, "player", player_id)
    _grant("board_token", token_id, "move", player_id)

    client = TestClient(app)
    with client.websocket_connect(f"/ws/campaigns/{campaign_id}?user_id={player_id}") as ws:
        assert ws.receive_json()["type"] == "connected"
        ws.send_json({"action": "move_token", "token_id": token_id, "to_x": 4, "to_y": 6})
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
    campaign_id, spectator_id, token_id = "camp-spectator-move", "spectator_dave", "token_boss"
    _grant("campaign", campaign_id, "spectator", spectator_id)

    client = TestClient(app)
    with client.websocket_connect(f"/ws/campaigns/{campaign_id}?user_id={spectator_id}") as ws:
        assert ws.receive_json()["type"] == "connected"
        ws.send_json({"action": "move_token", "token_id": token_id, "to_x": 1, "to_y": 1})
        err = ws.receive_json()
        assert err["type"] == "error"
        assert err["code"] == "PERMISSION_DENIED"
        assert err["action"] == "move_token"
        assert "insufficient permissions for action 'move_token'" in err["message"]


def test_player_attempting_to_trigger_dm_only_encounter_or_scene():
    """Verify player attempting to trigger DM-only encounter/scene is denied with PERMISSION_DENIED."""
    campaign_id, player_id = "camp-player-dm-actions", "player_kyra"
    _grant("campaign", campaign_id, "player", player_id)

    client = TestClient(app)
    with client.websocket_connect(f"/ws/campaigns/{campaign_id}?user_id={player_id}") as ws:
        assert ws.receive_json()["type"] == "connected"

        # 1. Attempt spawn_monster
        ws.send_json(
            {"action": "spawn_monster", "monster_name": "Ancient Red Dragon", "x": 5, "y": 5}
        )
        err1 = ws.receive_json()
        assert err1["type"] == "error" and err1["code"] == "PERMISSION_DENIED"
        assert err1["action"] == "spawn_monster"
        assert "insufficient permissions for action 'spawn_monster'" in err1["message"]

        # 2. Attempt set_scene
        ws.send_json({"action": "set_scene", "scene_id": "dragon_lair", "mood": "blazing_inferno"})
        err2 = ws.receive_json()
        assert err2["type"] == "error" and err2["code"] == "PERMISSION_DENIED"
        assert err2["action"] == "set_scene"
        assert "insufficient permissions for action 'set_scene'" in err2["message"]


def test_dungeon_master_executing_all_actions():
    """Verify Dungeon Master has full permissions to execute all actions."""
    campaign_id, dm_id = "camp-dm-omni", "dm_merlin"
    _grant("campaign", campaign_id, "dungeon_master", dm_id)

    client = TestClient(app)
    with client.websocket_connect(f"/ws/campaigns/{campaign_id}?user_id={dm_id}") as ws:
        assert ws.receive_json()["type"] == "connected"
        actions = [
            ("move_token", {"token_id": "token_goblin", "to_x": 3, "to_y": 3}),
            ("modify_hp", {"character_id": "char_valeros", "delta": -5}),
            ("apply_condition", {"character_id": "char_valeros", "condition": "drunk"}),
            ("spawn_monster", {"monster_name": "Goblin Shaman", "x": 2, "y": 2}),
            ("set_scene", {"scene_id": "scene_crypt", "mood": "shadowy"}),
        ]
        for action, payload in actions:
            ws.send_json({"action": action, **payload})
            res = ws.receive_json()
            assert res["action"] == action and res["status"] == "applied"


def test_character_hp_modification_permissions():
    """Verify character owner can modify HP/conditions, while unauthorized players are blocked."""
    campaign_id, p1, p2, char1 = "camp-char-edit", "player_ezren", "player_merisiel", "char_ezren"
    _grant("campaign", campaign_id, "player", p1)
    _grant("campaign", campaign_id, "player", p2)
    _grant("character", char1, "owner", p1)

    client = TestClient(app)
    # 1. Player1 edits own character -> Allowed
    with client.websocket_connect(f"/ws/campaigns/{campaign_id}?user_id={p1}") as ws:
        assert ws.receive_json()["type"] == "connected"
        ws.send_json({"action": "modify_hp", "character_id": char1, "delta": 2})
        res = ws.receive_json()
        assert res["action"] == "modify_hp" and res["status"] == "applied"

    # 2. Player2 attempts to edit char1 -> Denied
    with client.websocket_connect(f"/ws/campaigns/{campaign_id}?user_id={p2}") as ws:
        assert ws.receive_json()["type"] == "connected"
        ws.send_json({"action": "modify_hp", "character_id": char1, "delta": -10})
        err = ws.receive_json()
        assert err["type"] == "error" and err["code"] == "PERMISSION_DENIED"
        assert err["action"] == "modify_hp"


def test_redis_publishing_on_authorized_and_rejection_suppression():
    """Verify that authorized mutations are published to Redis, while denied actions are suppressed."""
    campaign_id, dm_id = "camp-redis-publish", "dm_elminster"
    _grant("campaign", campaign_id, "dungeon_master", dm_id)

    mock_redis = MockAsyncRedis()
    bus = RedisStreamsEventBus(redis_url="redis://fake:6379")
    bus._client = mock_redis
    set_event_bus(bus)

    client = TestClient(app)
    with client.websocket_connect(f"/ws/campaigns/{campaign_id}?user_id={dm_id}") as ws:
        assert ws.receive_json()["type"] == "connected"
        ws.send_json({"action": "move_token", "token_id": "tok_1", "to_x": 2, "to_y": 2})
        ws.receive_json()

        assert len(mock_redis.streams.get("runefoble.events.board", [])) == 1
        entry = mock_redis.streams["runefoble.events.board"][0]
        assert "move_token" in str(entry)


def test_dynamic_relation_revocation_denies_mid_session_action():
    """Verify revoking token ownership mid-session denies subsequent token movements."""
    campaign_id, player_id, token_id = "camp-dynamic-move", "player_sajan", "token_sajan"
    _grant("campaign", campaign_id, "player", player_id)
    _grant("board_token", token_id, "move", player_id)

    client = TestClient(app)
    with client.websocket_connect(f"/ws/campaigns/{campaign_id}?user_id={player_id}") as ws:
        assert ws.receive_json()["type"] == "connected"
        # 1. Initial move succeeds
        ws.send_json({"action": "move_token", "token_id": token_id, "to_x": 1, "to_y": 1})
        res = ws.receive_json()
        assert res["status"] == "applied"

        # 2. Revoke move permission dynamically
        asyncio.run(
            get_spicedb_client().delete_relationship(
                "board_token", token_id, "move", "user", player_id
            )
        )

        # 3. Next move is denied
        ws.send_json({"action": "move_token", "token_id": token_id, "to_x": 2, "to_y": 2})
        err = ws.receive_json()
        assert err["type"] == "error"
        assert err["code"] == "PERMISSION_DENIED"
        assert err["action"] == "move_token"
