"""Blackbox tests for ephemeral decal decay, animation finished lifecycle, and particle contracts."""

from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.usefixtures("board_campaign")


def test_ephemeral_decal_decay_over_two_rounds(
    client: TestClient, fireball_payload: dict[str, Any], board_campaign: str
) -> None:
    """Verify ephemeral scorched earth decals decay and naturally fade after 2 rounds."""
    board_id = f"board-{uuid4().hex[:8]}"
    client.post(
        "/api/v1/boards",
        json={"campaign_id": board_campaign, "board_id": board_id, "cols": 10, "rows": 10},
    )
    client.post(
        f"/api/v1/boards/{board_id}/spells/cast",
        json={**fireball_payload, "target_x": 4, "target_y": 4, "radius_ft": 15},
    )

    # Round 0: Decals present with 2 rounds remaining
    decals_r0 = client.get(f"/api/v1/boards/{board_id}/decals").json()
    assert len(decals_r0) > 0 and all(d["rounds_remaining"] == 2 for d in decals_r0)

    # Advance 1 Round: Decals decayed to 1 round remaining
    decay_r1 = client.post(f"/api/v1/boards/{board_id}/decals/decay", json={"rounds": 1}).json()
    assert len(decay_r1) > 0
    assert all(d["rounds_remaining"] == 1 and d["opacity"] < 0.9 for d in decay_r1)

    # Advance 2nd Round: Decals expire and are cleaned up
    decay_r2 = client.post(f"/api/v1/boards/{board_id}/decals/decay", json={"rounds": 1}).json()
    assert len(decay_r2) == 0, f"Expected 0 decals after 2 rounds, got {len(decay_r2)}"


def test_vfx_animation_finished_endpoint(client: TestClient, board_campaign: str) -> None:
    """Verify POST /api/v1/boards/{session_id}/vfx/finish persists and acknowledges completion."""
    board_id = f"board-{uuid4().hex[:8]}"
    client.post(
        "/api/v1/boards",
        json={"campaign_id": board_campaign, "board_id": board_id, "cols": 8, "rows": 8},
    )

    res = client.post(
        f"/api/v1/boards/{board_id}/vfx/finish",
        json={
            "animation_id": "vfx-test-1234",
            "spell_name": "Fireball",
            "target_x": 5,
            "target_y": 5,
            "duration_ms": 450,
        },
    )
    assert res.status_code == 200
    assert res.json()["status"] == "finished"
    assert res.json()["animation_id"] == "vfx-test-1234"
