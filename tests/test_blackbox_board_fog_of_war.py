"""Blackbox TDD tests for tactical board fog-of-war visibility, reveal, and shroud.

Governed by Hard Invariant 7 (Blackbox TDD with Frontdoor Setup).
Interacts strictly through public HTTP routes of board_state.
"""

from uuid import uuid4

from board_state.main import app
from fastapi.testclient import TestClient


def test_fog_of_war_visibility_and_manual_masking():
    """Verify fog-of-war visibility filtering, manual reveal, and manual shroud endpoints."""
    client = TestClient(app)
    board_id = f"board-{uuid4().hex[:8]}"

    # 1. Create a 10x10 board
    res = client.post("/api/v1/boards", json={"board_id": board_id, "cols": 10, "rows": 10})
    assert res.status_code == 200

    # 2. Place a friendly token at (2, 2) with vision radius 2
    res_tok = client.post(
        f"/api/v1/boards/{board_id}/tokens",
        json={
            "token_id": "valeros",
            "name": "Valeros",
            "x": 2,
            "y": 2,
            "is_friendly": True,
            "vision_radius": 2,
        },
    )
    assert res_tok.status_code == 200

    # Place a hostile monster at (8, 8)
    res_mon = client.post(
        f"/api/v1/boards/{board_id}/tokens",
        json={
            "token_id": "goblin-1",
            "name": "Goblin",
            "token_type": "monster",
            "x": 8,
            "y": 8,
            "is_friendly": False,
        },
    )
    assert res_mon.status_code == 200

    # 3. Check player perspective visibility (is_dm=False): goblin is omitted
    vis_player = client.get(f"/api/v1/boards/{board_id}/visibility?is_dm=false").json()
    assert [2, 2] in vis_player["revealed_cells"]
    assert [8, 8] not in vis_player["revealed_cells"]
    token_ids_player = [t["token_id"] for t in vis_player["tokens"]]
    assert "valeros" in token_ids_player
    assert "goblin-1" not in token_ids_player

    # 4. Manually reveal cell (8, 8) via /fog-of-war/reveal
    reveal_res = client.post(
        f"/api/v1/boards/{board_id}/fog-of-war/reveal",
        json={"cells": [[8, 8]]},
    )
    assert reveal_res.status_code == 200
    rev_data = reveal_res.json()
    assert [8, 8] in rev_data["revealed_cells"]

    # Now player perspective sees the goblin because (8, 8) is revealed
    vis_player_after = client.get(f"/api/v1/boards/{board_id}/visibility?is_dm=false").json()
    token_ids_after = [t["token_id"] for t in vis_player_after["tokens"]]
    assert "goblin-1" in token_ids_after

    # 5. Manually shroud cell (8, 8) via /fog-of-war/shroud
    shroud_res = client.post(
        f"/api/v1/boards/{board_id}/fog-of-war/shroud",
        json={"cells": [[8, 8]]},
    )
    assert shroud_res.status_code == 200
    shroud_data = shroud_res.json()
    assert [8, 8] not in shroud_data["revealed_cells"]

    # Player perspective no longer sees goblin
    vis_shrouded = client.get(f"/api/v1/boards/{board_id}/visibility?is_dm=false").json()
    assert "goblin-1" not in [t["token_id"] for t in vis_shrouded["tokens"]]

    # 6. Delete/remove goblin token via DELETE endpoint
    del_res = client.delete(f"/api/v1/boards/{board_id}/tokens/goblin-1")
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "removed"

    # Verify goblin is removed from board
    board_final = client.get(f"/api/v1/boards/{board_id}").json()
    assert "goblin-1" not in board_final["tokens"]
