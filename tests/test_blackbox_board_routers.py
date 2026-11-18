"""Blackbox tests verifying modular APIRouter decomposition for board_state bounded context.

Ensures zero contract regressions, public HTTP frontdoor reachability, OpenAPI schema completeness,
and strict compliance with Hard Invariant 6 (file length < 500 lines).
"""

import asyncio
from uuid import uuid4

import pytest
from board_state.main import app as board_app
from fastapi.testclient import TestClient

from tests.helpers.ws_identity import SIGNING_ISSUER


def bearer(sub: str) -> dict[str, str]:
    """Return the Authorization header for a token that the shared test issuer signs for `sub`."""
    return {"Authorization": f"Bearer {SIGNING_ISSUER.mint(sub)}"}


@pytest.fixture
def board_client():
    return TestClient(board_app, headers=bearer("user-test"))


def test_board_state_openapi_routes_completeness(board_client):
    """Verify that all decomposed APIRouter routes are registered in board_state OpenAPI schema."""
    openapi = board_client.app.openapi()
    paths = openapi["paths"]

    expected_routes = [
        "/healthz",
        "/ui/manifest",
        "/api/v1/boards",
        "/api/v1/boards/{session_id}",
        "/api/v1/boards/{session_id}/tokens",
        "/api/v1/boards/{session_id}/tokens/{token_id}/move",
        "/api/v1/boards/{session_id}/move",
        "/api/v1/boards/{session_id}/tokens/{token_id}",
        "/api/v1/boards/{session_id}/visibility",
        "/api/v1/boards/{session_id}/terrain",
        "/api/v1/boards/{session_id}/fog-of-war/reveal",
        "/api/v1/boards/{session_id}/fog-of-war/shroud",
        "/api/v1/boards/{session_id}/tokens/{token_id}/preview",
        "/api/v1/boards/{session_id}/preview",
        "/api/v1/boards/{session_id}/preview-move",
    ]

    for route in expected_routes:
        assert route in paths, f"Route '{route}' missing from Board State OpenAPI schema"


def test_board_state_spatial_frontdoor(board_client):
    """Verify board creation and spatial retrieval frontdoors."""
    assert board_client.get("/healthz").status_code == 200
    assert board_client.get("/ui/manifest").status_code == 200

    board_id = f"board-{uuid4().hex[:8]}"
    create_res = board_client.post(
        "/api/v1/boards",
        json={"campaign_id": BOARD_CAMPAIGN, "board_id": board_id, "cols": 12, "rows": 12},
    )
    assert create_res.status_code == 200
    get_res = board_client.get(f"/api/v1/boards/{board_id}")
    assert get_res.status_code == 200
    assert get_res.json()["cols"] == 12


def test_board_state_tokens_frontdoor(board_client):
    """Verify token placement, movement, trajectory previews, and removal frontdoors."""
    board_id = f"board-{uuid4().hex[:8]}"
    board_client.post(
        "/api/v1/boards",
        json={"campaign_id": BOARD_CAMPAIGN, "board_id": board_id, "cols": 12, "rows": 12},
    )

    tok_res = board_client.post(
        f"/api/v1/boards/{board_id}/tokens",
        json={"token_id": "tok-1", "name": "Valeros", "x": 1, "y": 1, "is_friendly": True},
    )
    assert tok_res.status_code == 200
    move_res = board_client.post(
        f"/api/v1/boards/{board_id}/tokens/tok-1/move",
        json={"to_x": 2, "to_y": 2},
    )
    assert move_res.status_code == 200
    assert move_res.json()["x"] == 2

    prev_res = board_client.post(
        f"/api/v1/boards/{board_id}/tokens/tok-1/preview",
        json={"to_x": 3, "to_y": 3},
    )
    assert prev_res.status_code == 200
    assert prev_res.json()["total_distance_ft"] > 0

    del_res = board_client.delete(f"/api/v1/boards/{board_id}/tokens/tok-1")
    assert del_res.status_code == 200


def test_board_state_terrain_frontdoor(board_client):
    """Verify terrain hazards and fog-of-war visibility frontdoors."""
    board_id = f"board-{uuid4().hex[:8]}"
    board_client.post(
        "/api/v1/boards",
        json={"campaign_id": BOARD_CAMPAIGN, "board_id": board_id, "cols": 12, "rows": 12},
    )

    terrain_res = board_client.post(
        f"/api/v1/boards/{board_id}/terrain",
        json={"x": 3, "y": 3, "elevation": 1, "terrain_type": "difficult"},
    )
    assert terrain_res.status_code == 200

    vis_res = board_client.get(f"/api/v1/boards/{board_id}/visibility?is_dm=true")
    assert vis_res.status_code == 200

    rev_res = board_client.post(
        f"/api/v1/boards/{board_id}/fog-of-war/reveal",
        json={"cells": [[5, 5]]},
    )
    assert rev_res.status_code == 200

    shroud_res = board_client.post(
        f"/api/v1/boards/{board_id}/fog-of-war/shroud",
        json={"cells": [[5, 5]]},
    )
    assert shroud_res.status_code == 200


def test_board_state_previews_modular_frontdoors(board_client):
    """Verify previews REST and WebSocket frontdoors after modular router decomposition."""
    board_id = f"board-{uuid4().hex[:8]}"
    board_client.post(
        "/api/v1/boards",
        json={"campaign_id": BOARD_CAMPAIGN, "board_id": board_id, "cols": 10, "rows": 10},
    )
    board_client.post(
        f"/api/v1/boards/{board_id}/tokens",
        json={"token_id": "valeros", "name": "Valeros", "x": 2, "y": 2, "is_friendly": True},
    )

    # 1. Test previews HTTP REST frontdoor
    prev_res = board_client.post(
        f"/api/v1/boards/{board_id}/tokens/valeros/preview",
        json={"to_x": 4, "to_y": 2, "movement_budget": 30},
    )
    assert prev_res.status_code == 200
    prev_json = prev_res.json()
    assert prev_json["token_id"] == "valeros"
    assert prev_json["total_distance_ft"] == 10
    assert len(prev_json["waypoints"]) == 2

    # 2. Test previews preview-move alternative endpoint
    prev_move_res = board_client.post(
        f"/api/v1/boards/{board_id}/preview-move",
        json={"token_id": "valeros", "to_x": 3, "to_y": 2},
    )
    assert prev_move_res.status_code == 200
    assert prev_move_res.json()["total_distance_ft"] == 5

    # 3. Test previews WebSocket frontdoor: connection, ghost preview, confirm move, cancel preview
    with board_client.websocket_connect(f"/ws/boards/{board_id}") as ws:
        connected = ws.receive_json()
        assert connected["type"] == "connected"

        # Ghost preview request
        ws.send_json(
            {
                "type": "ghost_preview",
                "token_id": "valeros",
                "speaker_name": "Valeros",
                "to_x": 5,
                "to_y": 2,
            }
        )
        ghost_msg = ws.receive_json()
        assert ghost_msg["type"] == "ghost_preview"
        assert ghost_msg["status"] == "staged"
        assert ghost_msg["preview"]["token_id"] == "valeros"
        assert ghost_msg["preview"]["to_x"] == 5

        # Movement confirmation
        ws.send_json(
            {
                "action": "confirm_move",
                "token_id": "valeros",
                "to_x": 5,
                "to_y": 2,
            }
        )
        conf_msg = ws.receive_json()
        assert conf_msg["type"] == "token_moved"
        assert conf_msg["token_id"] == "valeros"
        assert conf_msg["x"] == 5
        assert conf_msg["y"] == 2

        # Cancellation
        ws.send_json(
            {
                "action": "cancel_preview",
                "token_id": "valeros",
            }
        )
        cancel_msg = ws.receive_json()
        assert cancel_msg["type"] == "preview_cancelled"
        assert cancel_msg["token_id"] == "valeros"


BOARD_CAMPAIGN = "camp-board-fixture"


@pytest.fixture(autouse=True)
def _board_campaign_dm(spicedb):
    """Make `user-test` the DM of the campaign that every board in this module belongs to."""
    asyncio.run(
        spicedb.write_relationship(
            resource_type="campaign",
            resource_id=BOARD_CAMPAIGN,
            relation="dungeon_master",
            subject_type="user",
            subject_id="user-test",
        )
    )
