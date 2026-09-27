"""Blackbox tests verifying modular APIRouter decomposition for board_state bounded context.

Ensures zero contract regressions, public HTTP frontdoor reachability, OpenAPI schema completeness,
and strict compliance with Hard Invariant 6 (file length < 500 lines).
"""

from pathlib import Path
from uuid import uuid4

import pytest
from board_state.main import app as board_app
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parent.parent


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


def test_board_state_previews_modular_frontdoors(board_client):
    """Verify previews REST and WebSocket frontdoors after modular router decomposition."""
    board_id = f"board-{uuid4().hex[:8]}"
    board_client.post("/api/v1/boards", json={"board_id": board_id, "cols": 10, "rows": 10})
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


def test_previews_modular_file_invariants():
    """Verify file length limits for TASK-0188 previews router decomposition."""
    routers_dir = REPO_ROOT / "services" / "board_state" / "src" / "board_state" / "routers"

    previews_facade = routers_dir / "previews.py"
    previews_http = routers_dir / "previews_http.py"
    previews_ws = routers_dir / "previews_ws.py"
    previews_ws_actions = routers_dir / "previews_ws_actions.py"
    previews_ws_spells = routers_dir / "previews_ws_spells.py"

    assert previews_facade.exists(), "previews.py aggregator facade must exist"
    assert previews_http.exists(), "previews_http.py must exist"
    assert previews_ws.exists(), "previews_ws.py must exist"
    assert previews_ws_actions.exists(), "previews_ws_actions.py must exist"
    assert previews_ws_spells.exists(), "previews_ws_spells.py must exist"

    facade_lines = len(previews_facade.read_text().splitlines())
    http_lines = len(previews_http.read_text().splitlines())
    ws_lines = len(previews_ws.read_text().splitlines())
    actions_lines = len(previews_ws_actions.read_text().splitlines())
    spells_lines = len(previews_ws_spells.read_text().splitlines())

    # TASK-0188 DoD: previews.py strictly < 60 lines (and < 50 lines per spec)
    assert facade_lines < 60, f"previews.py exceeds 60 lines limit (current: {facade_lines})"

    # Extracted submodules strictly < 150 lines each
    assert http_lines < 150, f"previews_http.py exceeds 150 lines limit (current: {http_lines})"
    assert ws_lines < 150, f"previews_ws.py exceeds 150 lines limit (current: {ws_lines})"
    assert actions_lines < 150, (
        f"previews_ws_actions.py exceeds 150 lines limit (current: {actions_lines})"
    )
    assert spells_lines < 150, (
        f"previews_ws_spells.py exceeds 150 lines limit (current: {spells_lines})"
    )

    # Hard Invariant 6: All files in router directory must be strictly < 500 lines
    for py_file in routers_dir.glob("*.py"):
        line_count = len(py_file.read_text().splitlines())
        assert line_count < 500, (
            f"File {py_file.name} violates Hard Invariant 6 ({line_count} lines)"
        )
