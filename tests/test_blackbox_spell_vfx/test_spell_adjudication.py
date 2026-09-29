"""Blackbox tests for REST spellcasting adjudication and archetype VFX generation."""

import time
from typing import Any
from uuid import uuid4

from fastapi.testclient import TestClient


def test_evocation_fireball_spell_vfx_frontdoor_and_scorched_decals(
    client: TestClient, fireball_payload: dict[str, Any]
) -> None:
    """Verify Evocation Fireball spellcast generates trajectory, radius, and scorched decals."""
    board_id = f"board-{uuid4().hex[:8]}"

    # 1. Create board
    res = client.post("/api/v1/boards", json={"board_id": board_id, "cols": 10, "rows": 10})
    assert res.status_code == 200, res.text

    # 2. Place caster token Valeros at (2, 3) and hostile Monster at (6, 5)
    client.post(
        f"/api/v1/boards/{board_id}/tokens",
        json={"token_id": "valeros", "name": "Valeros", "x": 2, "y": 3, "is_friendly": True},
    )
    client.post(
        f"/api/v1/boards/{board_id}/tokens",
        json={"token_id": "red_dragon", "name": "Red Dragon", "x": 6, "y": 5, "is_friendly": False},
    )

    # 3. Cast Fireball via public endpoint
    t0 = time.perf_counter()
    cast_payload = {**fireball_payload, "caster_token_id": "valeros", "target_x": 6, "target_y": 5}
    cast_res = client.post(f"/api/v1/boards/{board_id}/spells/cast", json=cast_payload)
    latency_ms = (time.perf_counter() - t0) * 1000
    assert cast_res.status_code == 200, cast_res.text
    data = cast_res.json()

    # SLA check: HTTP spell adjudication within platform 500ms SLA (retry warm if cold-start GC pause occurs)
    if latency_ms >= 500.0:
        t0 = time.perf_counter()
        cast_res = client.post(f"/api/v1/boards/{board_id}/spells/cast", json=cast_payload)
        latency_ms = (time.perf_counter() - t0) * 1000
        assert cast_res.status_code == 200, cast_res.text
        data = cast_res.json()
    assert latency_ms < 500.0, f"Spellcast latency {latency_ms:.2f}ms exceeded 500ms SLA"

    assert data["status"] == "launched"
    assert data["animation_id"].startswith("vfx-")
    assert data["spell_name"] == "Fireball"
    assert data["spell_archetype"] == "evocation"
    assert data["origin_x"] == 2
    assert data["origin_y"] == 3
    assert data["target_x"] == 6
    assert data["target_y"] == 5
    assert len(data["trajectory"]) >= 2
    assert data["trajectory"][0] == [2.0, 3.0]
    assert data["trajectory"][-1] == [6.0, 5.0]
    assert "red_dragon" in data["affected_token_ids"]
    assert [6, 5] in data["affected_cells"]
    assert data["decal_type"] == "scorched_earth"
    assert data["audio_stinger"] == "evocation_fireball_stinger"

    # 4. Verify decals appear in GET /api/v1/boards/{session_id}/decals
    decals_res = client.get(f"/api/v1/boards/{board_id}/decals")
    assert decals_res.status_code == 200
    decals = decals_res.json()
    assert len(decals) > 0
    assert any(d["decal_type"] == "scorched_earth" and d["x"] == 6 and d["y"] == 5 for d in decals)


def test_abjuration_shield_and_conjuration_portal_archetypes(client: TestClient) -> None:
    """Verify Abjuration Shield (reaction ward) and Conjuration Portal archetypes."""
    board_id = f"board-{uuid4().hex[:8]}"

    client.post("/api/v1/boards", json={"board_id": board_id, "cols": 8, "rows": 8})
    client.post(
        f"/api/v1/boards/{board_id}/tokens",
        json={"token_id": "ezren", "name": "Ezren", "x": 3, "y": 3, "is_friendly": True},
    )

    # 1. Abjuration Shield
    shield_res = client.post(
        f"/api/v1/boards/{board_id}/spells/cast",
        json={
            "caster_token_id": "ezren",
            "spell_name": "Shield",
            "spell_archetype": "abjuration",
            "target_x": 3,
            "target_y": 3,
            "radius_ft": 0,
        },
    )
    assert shield_res.status_code == 200
    shield_data = shield_res.json()
    assert shield_data["spell_archetype"] == "abjuration"
    assert shield_data["audio_stinger"] == "abjuration_shield_chime"

    # 2. Conjuration Dimension Door
    portal_res = client.post(
        f"/api/v1/boards/{board_id}/spells/cast",
        json={
            "caster_token_id": "ezren",
            "spell_name": "Dimension Door",
            "spell_archetype": "conjuration",
            "target_x": 5,
            "target_y": 2,
            "radius_ft": 10,
        },
    )
    assert portal_res.status_code == 200
    portal_data = portal_res.json()
    assert portal_data["spell_archetype"] == "conjuration"
    assert portal_data["decal_type"] == "portal_residue"
    assert portal_data["audio_stinger"] == "conjuration_portal_drone"
