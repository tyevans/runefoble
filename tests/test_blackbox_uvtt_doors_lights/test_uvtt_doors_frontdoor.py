"""Blackbox tests for Universal VTT door geometry extraction, secret portals, and toggles."""

from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

from tests.test_blackbox_uvtt_doors_lights.conftest import grant_permission


def build_uvtt_with_doors() -> dict:
    """Build a UVTT map payload with standard, locked, and secret doors."""
    return {
        "format": 0.2,
        "resolution": {
            "map_origin": {"x": 0, "y": 0},
            "map_size": {"x": 20, "y": 20},
            "pixels_per_grid": 70,
        },
        "line_of_sight": [
            [{"x": 2.0, "y": 2.0}, {"x": 10.0, "y": 2.0}],
            [{"x": 10.0, "y": 2.0}, {"x": 10.0, "y": 10.0}],
        ],
        "portals": [
            {
                "id": "main_gate",
                "position": {"x": 5.0, "y": 2.0},
                "bounds": [{"x": 4.5, "y": 2.0}, {"x": 5.5, "y": 2.0}],
                "pivot": {"x": 4.5, "y": 2.0},
                "rotation": 0.0,
                "closed": True,
                "locked": False,
                "secret": False,
            },
            {
                "id": "vault_door",
                "position": {"x": 10.0, "y": 5.0},
                "bounds": [{"x": 10.0, "y": 4.5}, {"x": 10.0, "y": 5.5}],
                "pivot": {"x": 10.0, "y": 4.5},
                "rotation": 90.0,
                "closed": True,
                "locked": True,
                "secret": False,
            },
            {
                "id": "hidden_escape",
                "position": {"x": 8.0, "y": 2.0},
                "bounds": [{"x": 7.5, "y": 2.0}, {"x": 8.5, "y": 2.0}],
                "rotation": 0.0,
                "closed": True,
                "secret": True,
                "detection_dc": 18,
            },
            {
                "id": "open_archway",
                "position": {"x": 10.0, "y": 8.0},
                "bounds": [{"x": 10.0, "y": 7.5}, {"x": 10.0, "y": 8.5}],
                "rotation": 90.0,
                "closed": False,
                "open": True,
            },
        ],
        "lights": [],
    }


def test_uvtt_door_geometry_and_secret_portal_extraction(board_client: TestClient):
    """Verify extracting door coordinates, pivot hinges, statuses, and secret detection DCs."""
    board_id = f"board-doors-{uuid4().hex[:8]}"
    uvtt_data = build_uvtt_with_doors()

    # Frontdoor import via POST /board/{id}/import/uvtt
    response = board_client.post(
        f"/board/{board_id}/import/uvtt",
        json=uvtt_data,
    )
    assert response.status_code == 200, response.text
    data = response.json()

    assert data["status"] == "imported"
    doors = data["doors"]
    assert len(doors) == 4

    # 1. Main gate: closed, unlocked, pivot at (4.5, 2.0)
    main_gate = doors["main_gate"]
    assert main_gate["door_id"] == "main_gate"
    assert main_gate["x1"] == 4.5
    assert main_gate["y1"] == 2.0
    assert main_gate["x2"] == 5.5
    assert main_gate["y2"] == 2.0
    assert main_gate["pivot_x"] == 4.5
    assert main_gate["pivot_y"] == 2.0
    assert main_gate["status"] == "closed"
    assert main_gate["is_open"] is False
    assert main_gate["is_locked"] is False
    assert main_gate["is_secret"] is False

    # 2. Vault door: locked
    vault = doors["vault_door"]
    assert vault["status"] == "locked"
    assert vault["is_locked"] is True
    assert vault["is_open"] is False

    # 3. Hidden escape: secret with detection DC 18
    secret = doors["hidden_escape"]
    assert secret["is_secret"] is True
    assert secret["detection_dc"] == 18
    assert secret["status"] == "closed"

    # 4. Open archway: open
    arch = doors["open_archway"]
    assert arch["status"] == "open"
    assert arch["is_open"] is True

    # Public query projection verification via GET /board/{id}/doors
    doors_res = board_client.get(f"/board/{board_id}/doors")
    assert doors_res.status_code == 200
    assert len(doors_res.json()["doors"]) == 4


def test_door_toggle_state_transitions_http(board_client: TestClient):
    """Verify toggling door state machine over HTTP frontdoors."""
    board_id = f"board-toggle-{uuid4().hex[:8]}"
    uvtt_data = build_uvtt_with_doors()

    # Import map
    board_client.post(f"/board/{board_id}/import/uvtt", json=uvtt_data)

    # 1. Toggle closed main gate -> should open
    toggle_res1 = board_client.post(f"/board/{board_id}/doors/main_gate/toggle")
    assert toggle_res1.status_code == 200, toggle_res1.text
    door_data1 = toggle_res1.json()["door"]
    assert door_data1["status"] == "open"
    assert door_data1["is_open"] is True

    # Verify query projection updated
    get_res1 = board_client.get(f"/board/{board_id}/doors")
    assert get_res1.json()["doors"]["main_gate"]["is_open"] is True

    # 2. Toggle again -> should close
    toggle_res2 = board_client.post(f"/board/{board_id}/doors/main_gate/toggle")
    assert toggle_res2.status_code == 200
    assert toggle_res2.json()["door"]["is_open"] is False
    assert toggle_res2.json()["door"]["status"] == "closed"

    # 3. Explicit status toggle to locked
    toggle_res3 = board_client.post(
        f"/board/{board_id}/doors/main_gate/toggle",
        json={"status": "locked", "is_open": False},
    )
    assert toggle_res3.status_code == 200
    assert toggle_res3.json()["door"]["status"] == "locked"


def test_door_toggle_over_websocket_authorized_and_denied(gateway_client: TestClient):
    """Verify WebSocket Zanzibar authorization for door toggling."""
    campaign_id = f"camp-doors-{uuid4().hex[:8]}"
    player_id = "valeros_fighter"
    spectator_id = "spectator_sam"

    grant_permission("campaign", campaign_id, "player", player_id)
    grant_permission("campaign", campaign_id, "spectator", spectator_id)

    # 1. Player can toggle door over WebSocket
    with gateway_client.websocket_connect(f"/ws/campaigns/{campaign_id}?user_id={player_id}") as ws:
        assert ws.receive_json()["type"] == "connected"
        ws.send_json(
            {
                "action": "toggle_door",
                "door_id": "door-portcullis-1",
                "status": "open",
                "is_open": True,
            }
        )
        broadcast = ws.receive_json()
        assert broadcast["type"] == "toggle_door"
        assert broadcast["status"] == "open"
        assert broadcast["door_id"] == "door-portcullis-1"
        assert broadcast["is_open"] is True

    # 2. Spectator cannot toggle door (denied with PERMISSION_DENIED)
    with gateway_client.websocket_connect(
        f"/ws/campaigns/{campaign_id}?user_id={spectator_id}"
    ) as ws:
        assert ws.receive_json()["type"] == "connected"
        ws.send_json(
            {
                "action": "toggle_door",
                "door_id": "door-portcullis-1",
                "status": "open",
            }
        )
        err = ws.receive_json()
        assert err["type"] == "error"
        assert err["code"] == "PERMISSION_DENIED"
        assert "insufficient permissions" in err["message"]
