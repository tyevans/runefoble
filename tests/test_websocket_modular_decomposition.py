"""Blackbox & Modular Decomposition Tests for Gateway WebSocket Hub.

Governed by:
- ADR-0001: SpiceDB Zanzibar Object Authorization
- ADR-0005: Kubernetes-First Infrastructure with Helm and Kind
- ADR-0007: Real-Time Voice and Board Synchronization
- ADR-0009: Continuous Backlog Refinement and Technical Debt Management
- TASK-0080: Gateway WebSocket Hub and Action Validator Modular Decomposition
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from gateway_api.auth import get_spicedb_client, set_spicedb_client
from gateway_api.main import app, set_event_bus
from gateway_api.websocket import (
    CampaignConnectionManager,
    CampaignWebSocketManager,
    WebSocketActionValidator,
    authenticate_websocket,
    campaign_websocket_endpoint,
    default_action_validator,
    extract_subject_id,
    extract_token_from_websocket,
    ws_campaign_manager,
)
from gateway_api.websocket_auth import (
    authenticate_websocket as auth_fn,
)
from gateway_api.websocket_auth import (
    extract_subject_id as extract_sub_fn,
)
from gateway_api.websocket_auth import (
    extract_token_from_websocket as extract_tok_fn,
)
from gateway_api.websocket_endpoint import (
    campaign_websocket_endpoint as endpoint_fn,
)
from gateway_api.websocket_manager import (
    CampaignConnectionManager as ManagerClass,
)
from gateway_api.websocket_manager import (
    CampaignWebSocketManager as WebSocketManagerClass,
)
from gateway_api.websocket_manager import (
    ws_campaign_manager as manager_instance,
)
from gateway_api.websocket_validator import (
    DM_ACTIONS,
    HEALTH_ACTIONS,
    MOVE_ACTIONS,
)
from gateway_api.websocket_validator import (
    WebSocketActionValidator as ValidatorClass,
)
from gateway_api.websocket_validator import (
    default_action_validator as default_validator_instance,
)
from runefoble_auth.spicedb import MockSpiceDBClient, SpiceDBClient
from runefoble_platform.redis_bus import MockAsyncRedis, RedisStreamsEventBus


@pytest.fixture(autouse=True)
def reset_gateway_state():
    """Reset SpiceDB client and event bus before and after each test."""
    client = MockSpiceDBClient()
    set_spicedb_client(client)
    set_event_bus(None)
    yield
    set_spicedb_client(SpiceDBClient())
    set_event_bus(None)


def test_modular_file_length_invariants():
    """Verify that all decomposed WebSocket modules strictly comply with line limits (< 150 lines)."""
    base_dir = Path(__file__).resolve().parent.parent / "gateway" / "api" / "src" / "gateway_api"
    target_files = {
        "websocket_validator.py": 140,
        "websocket_manager.py": 100,
        "websocket_endpoint.py": 150,
        "websocket_auth.py": 150,
        "websocket.py": 130,
    }

    for filename, max_lines in target_files.items():
        file_path = base_dir / filename
        assert file_path.exists(), f"Expected module {filename} does not exist"
        line_count = len(file_path.read_text(encoding="utf-8").splitlines())
        assert line_count < max_lines, (
            f"File {filename} has {line_count} lines, exceeding task limit {max_lines}"
        )
        assert line_count < 150, (
            f"File {filename} has {line_count} lines, violating Hard Invariant 6 (<150)"
        )


def test_module_re_export_parity():
    """Verify facade re-exports match underlying submodules for complete backward compatibility."""
    assert WebSocketActionValidator is ValidatorClass
    assert default_action_validator is default_validator_instance
    assert CampaignConnectionManager is ManagerClass
    assert CampaignWebSocketManager is WebSocketManagerClass
    assert ws_campaign_manager is manager_instance
    assert campaign_websocket_endpoint is endpoint_fn
    assert extract_token_from_websocket is extract_tok_fn
    assert extract_subject_id is extract_sub_fn
    assert authenticate_websocket is auth_fn


@pytest.mark.asyncio
async def test_websocket_action_validator_direct_evaluation():
    """Verify WebSocketActionValidator logic against SpiceDB relationships directly."""
    spicedb = get_spicedb_client()
    validator = WebSocketActionValidator(spicedb)

    campaign_id = "camp-validator-direct"
    player_id = "user_direct_player"
    dm_id = "user_direct_dm"

    await spicedb.write_relationship("campaign", campaign_id, "view", "user", player_id)
    await spicedb.write_relationship("campaign", campaign_id, "dungeon_master", "user", dm_id)

    # validate_connect
    assert await validator.validate_connect(campaign_id, player_id) is True
    assert await validator.validate_connect(campaign_id, "stranger") is False

    # is_dungeon_master
    assert await validator.is_dungeon_master(campaign_id, dm_id) is True
    assert await validator.is_dungeon_master(campaign_id, player_id) is False

    # DM passes any action
    assert (
        await validator.validate_action(
            campaign_id, dm_id, "spawn_monster", {"monster": "Beholder"}
        )
        is True
    )

    # Player rejected for DM-only action
    assert (
        await validator.validate_action(
            campaign_id, player_id, "spawn_monster", {"monster": "Beholder"}
        )
        is False
    )

    # Action groupings
    assert "move_token" in MOVE_ACTIONS
    assert "modify_hp" in HEALTH_ACTIONS
    assert "spawn_monster" in DM_ACTIONS


def test_frontdoor_websocket_lifecycle_and_broadcast():
    """Frontdoor test: connect, mutate state, verify broadcast and Redis stream publishing."""
    campaign_id = "camp-frontdoor-flow"
    dm_id = "dm_gandalf"
    spicedb = get_spicedb_client()

    import asyncio

    asyncio.run(
        spicedb.write_relationship("campaign", campaign_id, "dungeon_master", "user", dm_id)
    )

    mock_redis = MockAsyncRedis()
    bus = RedisStreamsEventBus(redis_url="redis://fake:6379")
    bus._client = mock_redis
    set_event_bus(bus)

    client = TestClient(app)
    with client.websocket_connect(f"/ws/campaigns/{campaign_id}?user_id={dm_id}") as ws:
        connected_frame = ws.receive_json()
        assert connected_frame["type"] == "connected"
        assert connected_frame["campaign_id"] == campaign_id
        assert connected_frame["user_id"] == dm_id

        # Send action
        ws.send_json(
            {
                "action": "move_token",
                "token_id": "tok_hero",
                "to_x": 5,
                "to_y": 7,
            }
        )

        broadcast = ws.receive_json()
        assert broadcast["type"] == "move_token"
        assert broadcast["status"] == "applied"
        assert broadcast["campaign_id"] == campaign_id
        assert broadcast["token_id"] == "tok_hero"
        assert broadcast["to_x"] == 5
        assert broadcast["to_y"] == 7

        # Verify event stream dispatch
        events = mock_redis.streams.get("runefoble.events.board", [])
        assert len(events) == 1
        assert "tok_hero" in str(events[0])
