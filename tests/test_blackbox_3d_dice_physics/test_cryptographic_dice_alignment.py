"""Blackbox frontdoor tests for 3D dice physics and cryptographic alignment (TASK-0170).

Governed by:
- ADR-0006: Redis Streams Distributed Domain Event Streaming
- Hard Invariant 6: File length limit (< 500 lines)
- Hard Invariant 7: Blackbox TDD with Frontdoor Setup
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from board_state.dependencies import repo
from fastapi.testclient import TestClient
from runefoble_events.events import DiceSettled
from runefoble_platform.mock_redis import MockAsyncRedis


def _create_board(client: TestClient, cols: int = 10, rows: int = 10) -> str:
    """Helper to create a fresh tactical board via public frontdoor."""
    resp = client.post(
        "/api/v1/boards",
        json={"cols": cols, "rows": rows, "session_id": f"session-dice-phys-{uuid4()}"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["board_id"]


@pytest.mark.parametrize(
    ("dice_type", "expected_face"),
    [
        ("d4", 4),
        ("d6", 1),
        ("d8", 7),
        ("d10", 10),
        ("d12", 11),
        ("d20", 20),
    ],
)
def test_simulate_throw_cryptographic_alignment_all_polyhedral_types(
    client: TestClient,
    mock_bus: MockAsyncRedis,
    dice_type: str,
    expected_face: int,
) -> None:
    """Verify simulate-throw reliably resolves 100% to server-side cryptographic dice roll values."""
    board_id = _create_board(client)

    # 1. Post simulated 3D throw specifying cryptographic target face
    throw_resp = client.post(
        f"/api/v1/boards/{board_id}/physics/simulate-throw",
        json={
            "dice_type": dice_type,
            "face_value": expected_face,
            "origin_x": 1.5,
            "origin_y": 1.5,
            "origin_z": 3.0,
            "velocity_x": 4.5,
            "velocity_y": 4.0,
            "velocity_z": 1.8,
            "restitution": 0.5,
            "friction": 0.3,
            "seed": 999,
        },
    )
    assert throw_resp.status_code == 200, throw_resp.text
    data = throw_resp.json()

    # 2. Verify deterministic cryptographic alignment
    assert data["status"] == "settled"
    assert data["dice_type"] == dice_type
    assert data["face_value"] == expected_face
    assert data["bounces"] >= 1
    assert len(data["trajectory"]) > 0
    assert len(data["collisions"]) >= 1

    # 3. Verify settled coordinate boundaries
    settled_cell = data["settled_cell"]
    assert 0 <= settled_cell[0] < 10
    assert 0 <= settled_cell[1] < 10

    # 4. Verify domain event DiceSettled emitted to event store
    store = repo.event_store
    matching_events = [
        env.event
        for env in store._events
        if (
            isinstance(env.event, DiceSettled)
            or getattr(env.event, "event_type", "")
            in ("runefoble.events.board.dice.settled", "board.dice.settled")
        )
        and getattr(env.event, "dice_id", None) == data["dice_id"]
    ]
    assert len(matching_events) == 1
    settled_evt = matching_events[0]
    assert settled_evt.face_value == expected_face
    assert settled_evt.dice_type == dice_type
    assert settled_evt.bounces == data["bounces"]


def test_simulate_throw_boundary_bounce_and_energy_dissipation(
    client: TestClient,
    mock_bus: MockAsyncRedis,
) -> None:
    """Verify high velocity throw ricochets off tray perimeters and settles within bounds."""
    board_id = _create_board(client, cols=8, rows=8)

    throw_resp = client.post(
        f"/api/v1/boards/{board_id}/physics/simulate-throw",
        json={
            "dice_type": "d20",
            "target_face_value": 18,
            "origin_x": 1.0,
            "origin_y": 1.0,
            "origin_z": 2.5,
            "velocity_x": 8.0,
            "velocity_y": 7.5,
            "velocity_z": 2.0,
            "restitution": 0.55,
            "friction": 0.28,
        },
    )
    assert throw_resp.status_code == 200, throw_resp.text
    data = throw_resp.json()

    assert data["face_value"] == 18
    assert data["bounces"] >= 2
    # Verify collision impacts contain boundary contacts
    boundary_cols = [c for c in data["collisions"] if c.get("type") == "boundary"]
    assert len(boundary_cols) >= 1
    for col in boundary_cols:
        assert col["energy"] > 0


def test_simulate_throw_without_target_generates_valid_polyhedral_face(
    client: TestClient,
    mock_bus: MockAsyncRedis,
) -> None:
    """Verify standard roll without forced target generates valid face within sides range."""
    board_id = _create_board(client)

    throw_resp = client.post(
        f"/api/v1/boards/{board_id}/physics/simulate-throw",
        json={
            "dice_type": "d12",
            "origin_x": 2.0,
            "origin_y": 2.0,
            "origin_z": 3.0,
            "velocity_x": 3.5,
            "velocity_y": 3.5,
            "velocity_z": 1.5,
        },
    )
    assert throw_resp.status_code == 200, throw_resp.text
    data = throw_resp.json()

    assert 1 <= data["face_value"] <= 12
    assert data["status"] == "settled"
    assert data["bounces"] >= 1
