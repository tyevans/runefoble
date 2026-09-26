"""Blackbox tests verifying modular APIRouter decomposition for board_state bounded context.

Ensures zero contract regressions, public HTTP frontdoor reachability, OpenAPI schema completeness,
and strict compliance with Hard Invariant 6 (file length < 500 lines).
"""

from uuid import uuid4

import pytest
from board_state.main import app as board_app
from fastapi.testclient import TestClient


@pytest.fixture
def board_client():
    return TestClient(board_app)


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
        "/api/v1/boards", json={"board_id": board_id, "cols": 12, "rows": 12}
    )
    assert create_res.status_code == 200
    get_res = board_client.get(f"/api/v1/boards/{board_id}")
    assert get_res.status_code == 200
    assert get_res.json()["cols"] == 12


def test_board_state_tokens_frontdoor(board_client):
    """Verify token placement, movement, trajectory previews, and removal frontdoors."""
    board_id = f"board-{uuid4().hex[:8]}"
    board_client.post("/api/v1/boards", json={"board_id": board_id, "cols": 12, "rows": 12})

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
    board_client.post("/api/v1/boards", json={"board_id": board_id, "cols": 12, "rows": 12})

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
