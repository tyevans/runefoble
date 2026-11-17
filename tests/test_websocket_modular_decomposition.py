"""Blackbox & Modular Decomposition Tests for Gateway WebSocket Hub.

Governed by:
- ADR-0001: SpiceDB Zanzibar Object Authorization
- ADR-0005: Kubernetes-First Infrastructure with Helm and Kind
- ADR-0007: Real-Time Voice and Board Synchronization
- ADR-0009: Continuous Backlog Refinement and Technical Debt Management
- TASK-0080: Gateway WebSocket Hub and Action Validator Modular Decomposition
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from gateway_api.main import app, set_event_bus
from gateway_api.websocket import (
    CampaignConnectionManager,
    CampaignWebSocketManager,
    WebSocketActionValidator,
    admit_gateway_websocket,
    campaign_websocket_endpoint,
    default_action_validator,
    ws_campaign_manager,
)
from gateway_api.websocket_auth import (
    admit_gateway_websocket as admit_fn,
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
from runefoble_auth.factory import get_spicedb_client
from runefoble_platform.redis_bus import MockAsyncRedis, RedisStreamsEventBus

from tests.helpers.ws_identity import ws_subprotocols

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")


@pytest.fixture(autouse=True)
def reset_gateway_state():
    """Reset SpiceDB client and event bus before and after each test."""
    set_event_bus(None)
    yield
    set_event_bus(None)


def test_module_re_export_parity():
    """Verify facade re-exports match underlying submodules for complete backward compatibility."""
    assert WebSocketActionValidator is ValidatorClass
    assert default_action_validator is default_validator_instance
    assert CampaignConnectionManager is ManagerClass
    assert CampaignWebSocketManager is WebSocketManagerClass
    assert ws_campaign_manager is manager_instance
    assert campaign_websocket_endpoint is endpoint_fn
    assert admit_gateway_websocket is admit_fn


@pytest.mark.asyncio
async def test_websocket_action_validator_direct_evaluation():
    """Verify WebSocketActionValidator logic against SpiceDB relationships directly."""
    spicedb = get_spicedb_client()
    validator = WebSocketActionValidator(spicedb)

    campaign_id = "camp-validator-direct"
    player_id = "user_direct_player"
    dm_id = "user_direct_dm"

    await spicedb.write_relationship("campaign", campaign_id, "spectator", "user", player_id)
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
    with client.websocket_connect(
        f"/ws/campaigns/{campaign_id}", subprotocols=ws_subprotocols(dm_id)
    ) as ws:
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
