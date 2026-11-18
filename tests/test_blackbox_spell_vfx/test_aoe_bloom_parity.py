"""Blackbox parity tests: AoE template evaluation and spell VFX bloom share one sphere rule.

Governed by:
- TASK-0733: Square-grid AoE origin on the cell centre, one sphere rule
- Hard Invariant 7: Blackbox TDD with frontdoor setup (HTTP only)
"""

from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

BOARD_COLS = 20
BOARD_ROWS = 20


@pytest.fixture
def board_id(client: TestClient) -> str:
    board = f"board-{uuid4().hex[:8]}"
    res = client.post(
        "/api/v1/boards", json={"board_id": board, "cols": BOARD_COLS, "rows": BOARD_ROWS}
    )
    assert res.status_code == 200, res.text
    return board


def _evaluate_sphere(
    client: TestClient, board_id: str, origin: tuple[int, int], radius_ft: float
) -> set[tuple[int, int]]:
    res = client.post(
        f"/api/v1/boards/{board_id}/aoe/evaluate",
        json={
            "shape": "sphere",
            "origin_x": origin[0],
            "origin_y": origin[1],
            "radius_ft": radius_ft,
        },
    )
    assert res.status_code == 200, res.text
    return {(cell[0], cell[1]) for cell in res.json()["affected_cells"]}


def _bloom_sphere(
    client: TestClient,
    board_id: str,
    fireball_payload: dict[str, Any],
    target: tuple[int, int],
    radius_ft: int,
) -> set[tuple[int, int]]:
    payload = {
        **fireball_payload,
        "target_x": target[0],
        "target_y": target[1],
        "radius_ft": radius_ft,
    }
    res = client.post(f"/api/v1/boards/{board_id}/spells/cast", json=payload)
    assert res.status_code == 200, res.text
    return {(cell[0], cell[1]) for cell in res.json()["affected_cells"]}


def test_five_foot_sphere_covers_the_origin_cell_and_its_four_neighbours(
    client: TestClient, board_id: str
) -> None:
    """A 5 ft sphere on cell (5, 5) is centred on that cell, so it covers the cross of five cells."""
    cells = _evaluate_sphere(client, board_id, (5, 5), 5.0)

    assert cells == {(5, 5), (4, 5), (6, 5), (5, 4), (5, 6)}


def test_spell_bloom_and_aoe_sphere_return_the_same_cells(
    client: TestClient, board_id: str, fireball_payload: dict[str, Any]
) -> None:
    """A 20 ft sphere from the same cell gives the same cell set from the AoE and the spell bloom."""
    aoe_cells = _evaluate_sphere(client, board_id, (5, 5), 20.0)
    bloom_cells = _bloom_sphere(client, board_id, fireball_payload, (5, 5), 20)

    assert aoe_cells == bloom_cells
    assert len(aoe_cells) == 49


def test_socket_aoe_evaluate_rejects_fractional_origin(client: TestClient, board_id: str) -> None:
    """A socket aoe_evaluate with a half-cell origin gets an error frame, not a shifted preview."""
    with client.websocket_connect(f"/ws/boards/{board_id}") as ws:
        ws.receive_json()  # connected frame
        ws.send_json(
            {
                "action": "aoe_evaluate",
                "shape": "sphere",
                "origin_x": 2.5,
                "origin_y": 2,
                "radius_ft": 5,
            }
        )
        frame = ws.receive_json()

    assert frame["type"] == "error"
    assert frame["status"] == 422
