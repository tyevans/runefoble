"""Foley soundboard and WebAudio ducking tests for Soundscape UI (TASK-0154).

Governed by:
- ADR-0006: Redis Streams Event Bus
- ADR-0007: API Gateway Architecture and Service Endpoints
- Hard Invariant 6: File length limit (< 500 lines)
- Hard Invariant 7: Blackbox TDD with Frontdoor Setup
"""

from __future__ import annotations

import asyncio
import math
from typing import Any

from fastapi.testclient import TestClient
from gateway_api.auth import set_spicedb_client as set_gw_spicedb_client
from runefoble_auth.mock_spicedb import MockSpiceDBClient


def test_rest_data_binding_foley_cue_trigger(
    client: TestClient, sample_foley_cue: dict[str, Any]
) -> None:
    """Verify POST /api/v1/soundscape/cue triggers acoustic foley effects with ducking."""
    resp = client.post("/api/v1/soundscape/cue", json=sample_foley_cue)
    assert resp.status_code == 200
    data = resp.json()
    assert data["session_id"] == sample_foley_cue["session_id"]
    assert data["cue_name"] == sample_foley_cue["cue_name"]
    assert data["status"] == "triggered"
    assert data["duck_music"] is True


def test_rest_data_binding_webaudio_ducking(client: TestClient) -> None:
    """Verify POST /api/v1/soundscape/duck toggles -12dB attenuation coordinator."""
    duck_resp = client.post(
        "/api/v1/soundscape/duck",
        json={"session_id": "sess-ui-01", "is_ducked": True, "reason": "speech"},
    )
    assert duck_resp.status_code == 200
    data = duck_resp.json()
    assert data["is_ducked"] is True
    assert data["attenuation_db"] == -12.0
    assert math.isclose(data["effective_gain"], 0.2512, rel_tol=1e-3)

    unduck_resp = client.post(
        "/api/v1/soundscape/duck",
        json={"session_id": "sess-ui-01", "is_ducked": False, "reason": "speech_ended"},
    )
    assert unduck_resp.status_code == 200
    unduck_data = unduck_resp.json()
    assert unduck_data["is_ducked"] is False
    assert unduck_data["attenuation_db"] == 0.0
    assert unduck_data["effective_gain"] == 1.0


def test_gateway_websocket_soundscape_broadcast(gateway_client: TestClient) -> None:
    """Verify soundscape acoustic cues fan out through the campaign WebSocket."""
    campaign_id = "camp-soundscape-ws-01"
    dm_user = "dm-evelyn"

    mock_db = MockSpiceDBClient()
    set_gw_spicedb_client(mock_db)

    asyncio.run(
        mock_db.write_relationship(
            resource_type="campaign",
            resource_id=campaign_id,
            relation="dungeon_master",
            subject_type="user",
            subject_id=dm_user,
        )
    )

    with gateway_client.websocket_connect(f"/ws/campaigns/{campaign_id}?user_id={dm_user}") as ws:
        connected_frame = ws.receive_json()
        assert connected_frame["type"] == "connected"

        # Broadcast soundboard foley trigger action
        ws.send_json(
            {
                "action": "soundscape_cue",
                "cue_name": "thunder",
                "duck_music": True,
                "volume_gain": 1.1,
                "session_id": "sess-ws-1",
            }
        )

        broadcast = ws.receive_json()
        assert broadcast["type"] == "soundscape_cue"
        assert broadcast["action"] == "soundscape_cue"
        assert broadcast["cue_name"] == "thunder"
        assert broadcast["duck_music"] is True
        assert broadcast["status"] == "applied"
        assert broadcast["user_id"] == dm_user
