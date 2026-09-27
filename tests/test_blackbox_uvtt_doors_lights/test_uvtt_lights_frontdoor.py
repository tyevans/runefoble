"""Blackbox tests for Universal VTT point lights, radiance mapping, and dynamic placement."""

from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

from tests.test_blackbox_uvtt_doors_lights.conftest import grant_permission


def build_uvtt_with_lights() -> dict:
    """Build a UVTT map payload with various point light sources."""
    return {
        "format": 0.2,
        "resolution": {
            "map_origin": {"x": 0, "y": 0},
            "map_size": {"x": 20, "y": 20},
            "pixels_per_grid": 70,
        },
        "line_of_sight": [],
        "portals": [],
        "lights": [
            {
                "id": "brazier_north",
                "position": {"x": 5.0, "y": 4.0},
                "range": 8.0,
                "color": "ffff9933",
                "intensity": 0.9,
                "flicker": 0.35,
                "shadows": True,
            },
            {
                "id": "arcane_orb",
                "position": {"x": 12.0, "y": 14.0},
                "bright_radius": 15.0,
                "dim_radius": 30.0,
                "color": "#3366ff",
                "intensity": 1.2,
                "flicker_intensity": 0.1,
                "shadows": False,
            },
        ],
    }


def test_uvtt_light_mapping_and_radiance_models(board_client: TestClient):
    """Verify mapping UVTT light sources into bright/dim radius and flicker models."""
    board_id = f"board-lights-{uuid4().hex[:8]}"
    uvtt_data = build_uvtt_with_lights()

    # Frontdoor import via POST /board/{id}/import/uvtt
    response = board_client.post(f"/board/{board_id}/import/uvtt", json=uvtt_data)
    assert response.status_code == 200, response.text
    data = response.json()

    assert data["status"] == "imported"
    lights = data["lights"]
    assert len(lights) == 2

    # 1. Brazier: range=8.0 -> dim_radius=8.0, bright_radius=4.0, flicker=0.35
    brazier = next(
        light_src
        for light_src in lights
        if light_src.get("light_id") == "brazier_north" or light_src.get("id") == "brazier_north"
    )
    assert brazier["x"] == 5.0
    assert brazier["y"] == 4.0
    assert brazier["dim_radius"] == 8.0
    assert brazier["bright_radius"] == 4.0
    assert brazier["flicker_intensity"] == 0.35
    assert brazier["color_hex"] == "#ffff9933"
    assert brazier["shadows"] is True

    # 2. Arcane orb: explicit bright_radius=15.0, dim_radius=30.0, shadows=False
    orb = next(
        light_src
        for light_src in lights
        if light_src.get("light_id") == "arcane_orb" or light_src.get("id") == "arcane_orb"
    )
    assert orb["bright_radius"] == 15.0
    assert orb["dim_radius"] == 30.0
    assert orb["color_hex"] == "#3366ff"
    assert orb["shadows"] is False

    # Observable public projection via GET /board/{id}/lights
    get_res = board_client.get(f"/board/{board_id}/lights")
    assert get_res.status_code == 200
    assert len(get_res.json()["lights"]) == 2


def test_dynamic_light_placement_http(board_client: TestClient):
    """Verify placing new point light sources via HTTP frontdoors."""
    board_id = f"board-light-place-{uuid4().hex[:8]}"

    # Frontdoor placement: POST /board/{id}/lights
    req_payload = {
        "light_id": "torch_01",
        "x": 7.5,
        "y": 8.5,
        "color_hex": "#ffaa22",
        "bright_radius": 20.0,
        "dim_radius": 40.0,
        "flicker_intensity": 0.25,
        "intensity": 1.0,
        "shadows": True,
    }
    resp = board_client.post(f"/board/{board_id}/lights", json=req_payload)
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "success"
    assert resp.json()["light_id"] == "torch_01"

    # Verify query projection
    get_res = board_client.get(f"/board/{board_id}/lights")
    assert get_res.status_code == 200
    lights = get_res.json()["lights"]
    assert any(
        light_src["light_id"] == "torch_01" and light_src["bright_radius"] == 20.0
        for light_src in lights
    )


def test_light_placement_over_websocket_authorized_and_denied(gateway_client: TestClient):
    """Verify WebSocket Zanzibar authorization for dynamic light placement."""
    campaign_id = f"camp-lights-{uuid4().hex[:8]}"
    dm_id = "dm_evelyn"
    spectator_id = "spectator_sam"

    grant_permission("campaign", campaign_id, "dungeon_master", dm_id)
    grant_permission("campaign", campaign_id, "spectator", spectator_id)

    # 1. DM can place light over WebSocket
    with gateway_client.websocket_connect(f"/ws/campaigns/{campaign_id}?user_id={dm_id}") as ws:
        assert ws.receive_json()["type"] == "connected"
        ws.send_json(
            {
                "action": "place_light",
                "light_id": "campfire_01",
                "x": 10.0,
                "y": 10.0,
                "color_hex": "#ff7700",
                "bright_radius": 10.0,
                "dim_radius": 20.0,
            }
        )
        broadcast = ws.receive_json()
        assert broadcast["type"] == "place_light"
        assert broadcast["status"] == "applied"
        assert broadcast["light_id"] == "campfire_01"

    # 2. Spectator cannot place light (denied with PERMISSION_DENIED)
    with gateway_client.websocket_connect(
        f"/ws/campaigns/{campaign_id}?user_id={spectator_id}"
    ) as ws:
        assert ws.receive_json()["type"] == "connected"
        ws.send_json(
            {
                "action": "place_light",
                "light_id": "cheat_light",
                "x": 1.0,
                "y": 1.0,
            }
        )
        err = ws.receive_json()
        assert err["type"] == "error"
        assert err["code"] == "PERMISSION_DENIED"
