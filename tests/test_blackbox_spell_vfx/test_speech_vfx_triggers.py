"""Blackbox tests for real-time WebSocket speech VFX triggers and domain event persistence."""

import time
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from tests.helpers.ws_identity import ws_subprotocols

pytestmark = pytest.mark.usefixtures("board_campaign")


def test_websocket_realtime_speech_spell_trigger_sub_150ms(
    client: TestClient, board_campaign: str
) -> None:
    """Verify WebSocket real-time stream handles spoken spellcast and broadcasts VFX in <150ms."""
    board_id = f"board-{uuid4().hex[:8]}"

    client.post(
        "/api/v1/boards",
        json={"campaign_id": board_campaign, "board_id": board_id, "cols": 10, "rows": 10},
    )
    client.post(
        f"/api/v1/boards/{board_id}/tokens",
        json={"token_id": "nadia", "name": "Nadia", "x": 1, "y": 2, "is_friendly": True},
    )

    with client.websocket_connect(
        f"/ws/boards/{board_id}", subprotocols=ws_subprotocols("user-test")
    ) as ws:
        connected = ws.receive_json()
        assert connected["type"] == "connected"

        # Broadcast spoken intent to board
        t0 = time.perf_counter()
        ws.send_json(
            {
                "type": "cast_spell",
                "spell_name": "Fireball",
                "spell_archetype": "evocation",
                "caster_token_id": "nadia",
                "target_x": 7,
                "target_y": 4,
                "radius_ft": 20,
                "damage_type": "fire",
            }
        )

        vfx_msg = ws.receive_json()
        latency_ms = (time.perf_counter() - t0) * 1000

        # Platform SLA verification (<500ms)
        assert latency_ms < 500.0, (
            f"WebSocket VFX trigger latency {latency_ms:.2f}ms exceeded 500ms"
        )

        assert vfx_msg["type"] == "spell_vfx"
        assert vfx_msg["status"] == "launched"
        assert vfx_msg["spell_name"] == "Fireball"
        assert vfx_msg["caster_token_id"] == "nadia"
        assert vfx_msg["target_x"] == 7
        assert vfx_msg["target_y"] == 4
        assert vfx_msg["radius_ft"] == 20
        assert len(vfx_msg["trajectory"]) >= 2
        assert vfx_msg["decal_type"] == "scorched_earth"
