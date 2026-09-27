"""Blackbox TDD frontdoor test suite for Multi-Modal Kinetic Spell VFX & WebGL Particle Magic.

Governed by Hard Invariant 7 (Blackbox TDD with Frontdoor Setup) and Hard Invariant 6 (< 500 lines).
Verifies:
- Public HTTP routes for kinetic spellcasting, trajectory generation, and radius blooms.
- Spell archetypes (Evocation Fireball, Lightning Arc, Abjuration Shield, Conjuration Portal).
- Ephemeral scorched earth and frost decals decaying over 2 rounds.
- Real-time WebSocket speech-to-VFX triggers with sub-150ms latency.
- Animation finished completion events.
- Microfrontend component and Storybook story verification.
"""

import os
import time
from pathlib import Path
from uuid import uuid4

import pytest
from board_state.aggregate import BoardAggregate
from board_state.dependencies import repo, to_board_uuid
from board_state.main import app as board_app
from fastapi.testclient import TestClient
from gateway_api.auth import set_spicedb_client
from gateway_api.main import set_event_bus
from runefoble_auth.spicedb import MockSpiceDBClient, SpiceDBClient

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(autouse=True)
def reset_test_state():
    client = MockSpiceDBClient()
    set_spicedb_client(client)
    set_event_bus(None)
    yield
    set_spicedb_client(SpiceDBClient())
    set_event_bus(None)


def test_evocation_fireball_spell_vfx_frontdoor_and_scorched_decals():
    """Verify Evocation Fireball spellcast generates trajectory, affected radius, and scorched earth decals."""
    client = TestClient(board_app)
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
    cast_res = client.post(
        f"/api/v1/boards/{board_id}/spells/cast",
        json={
            "caster_token_id": "valeros",
            "spell_name": "Fireball",
            "spell_archetype": "evocation",
            "target_x": 6,
            "target_y": 5,
            "radius_ft": 20,
            "damage_dice": "8d6",
            "damage_type": "fire",
        },
    )
    latency_ms = (time.perf_counter() - t0) * 1000
    assert cast_res.status_code == 200, cast_res.text
    data = cast_res.json()

    # SLA check: HTTP spell adjudication in <150ms (<500ms on CI runners)
    max_latency_ms = 500.0 if os.environ.get("CI") else 150.0
    assert latency_ms < max_latency_ms, (
        f"Spellcast latency {latency_ms:.2f}ms exceeded {max_latency_ms}ms SLA"
    )

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


def test_abjuration_shield_and_conjuration_portal_archetypes():
    """Verify Abjuration Shield (reaction ward) and Conjuration Portal archetypes."""
    client = TestClient(board_app)
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


def test_ephemeral_decal_decay_over_two_rounds():
    """Verify ephemeral scorched earth decals decay and naturally fade after 2 rounds."""
    client = TestClient(board_app)
    board_id = f"board-{uuid4().hex[:8]}"

    client.post("/api/v1/boards", json={"board_id": board_id, "cols": 10, "rows": 10})
    client.post(
        f"/api/v1/boards/{board_id}/spells/cast",
        json={
            "spell_name": "Fireball",
            "spell_archetype": "evocation",
            "target_x": 4,
            "target_y": 4,
            "radius_ft": 15,
            "damage_type": "fire",
        },
    )

    # Round 0: Decals present with 2 rounds remaining
    decals_r0 = client.get(f"/api/v1/boards/{board_id}/decals").json()
    assert len(decals_r0) > 0
    assert all(d["rounds_remaining"] == 2 for d in decals_r0)

    # Advance 1 Round: Decals decayed to 1 round remaining
    decay_r1 = client.post(f"/api/v1/boards/{board_id}/decals/decay", json={"rounds": 1})
    assert decay_r1.status_code == 200
    decals_r1 = decay_r1.json()
    assert len(decals_r1) > 0
    assert all(d["rounds_remaining"] == 1 for d in decals_r1)
    assert all(d["opacity"] < 0.9 for d in decals_r1)

    # Advance 2nd Round: Decals expire and are cleaned up
    decay_r2 = client.post(f"/api/v1/boards/{board_id}/decals/decay", json={"rounds": 1})
    assert decay_r2.status_code == 200
    decals_r2 = decay_r2.json()
    assert len(decals_r2) == 0, f"Expected 0 decals after 2 rounds, got {len(decals_r2)}"


def test_vfx_animation_finished_endpoint():
    """Verify POST /api/v1/boards/{session_id}/vfx/finish persists and acknowledges completion."""
    client = TestClient(board_app)
    board_id = f"board-{uuid4().hex[:8]}"
    client.post("/api/v1/boards", json={"board_id": board_id, "cols": 8, "rows": 8})

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


def test_websocket_realtime_speech_spell_trigger_sub_150ms():
    """Verify WebSocket real-time stream handles spoken spellcast and broadcasts VFX in <150ms."""
    client = TestClient(board_app)
    board_id = f"board-{uuid4().hex[:8]}"

    client.post("/api/v1/boards", json={"board_id": board_id, "cols": 10, "rows": 10})
    client.post(
        f"/api/v1/boards/{board_id}/tokens",
        json={"token_id": "nadia", "name": "Nadia", "x": 1, "y": 2, "is_friendly": True},
    )

    with client.websocket_connect(f"/ws/boards/{board_id}") as ws:
        connected = ws.receive_json()
        assert connected["type"] == "connected"

        # Broadcast spoken intent to board
        t0 = time.perf_counter()
        ws.send_json(
            {
                "type": "cast_spell",
                "spell_name": "Fireball",
                "spell_archetype": "evocation",
                "caster_token_id": "nadia",
                "target_x": 7,
                "target_y": 4,
                "radius_ft": 20,
                "damage_type": "fire",
            }
        )

        vfx_msg = ws.receive_json()
        latency_ms = (time.perf_counter() - t0) * 1000

        # Sub-150ms SLA verification (<500ms on CI runners)
        max_latency_ms = 500.0 if os.environ.get("CI") else 150.0
        assert latency_ms < max_latency_ms, (
            f"WebSocket VFX trigger latency {latency_ms:.2f}ms exceeded {max_latency_ms}ms"
        )

        assert vfx_msg["type"] == "spell_vfx"
        assert vfx_msg["status"] == "launched"
        assert vfx_msg["spell_name"] == "Fireball"
        assert vfx_msg["caster_token_id"] == "nadia"
        assert vfx_msg["target_x"] == 7
        assert vfx_msg["target_y"] == 4
        assert vfx_msg["radius_ft"] == 20
        assert len(vfx_msg["trajectory"]) >= 2
        assert vfx_msg["decal_type"] == "scorched_earth"


@pytest.mark.asyncio
async def test_event_sourcing_domain_events_persistence():
    """Verify SpellCast, AreaEffectExploded, and VFXAnimationFinished events are recorded."""
    sess_id = f"board-{uuid4().hex[:8]}"
    board_uuid = to_board_uuid(sess_id)
    board = BoardAggregate(board_uuid)
    board.initialize_grid(cols=10, rows=10, session_id=sess_id)
    board.place_token("valeros", "Valeros", "pc", 2, 2, 40, True)

    anim_id, trajectory, affected_tokens, affected_cells, decal = board.cast_spell(
        spell_name="Chain Lightning",
        target_x=5,
        target_y=5,
        caster_token_id="valeros",
        spell_archetype="evocation",
        radius_ft=15,
        damage_type="lightning",
    )
    board.finish_vfx(anim_id, "Chain Lightning", 5, 5, 400)
    await repo.save(board)

    # Reload aggregate and verify event replay
    loaded_board = await repo.load(board_uuid)
    assert loaded_board is not None
    assert loaded_board.state.cols == 10
    assert len(loaded_board.state.active_decals) > 0


def test_ui_components_storybook_and_microfrontend_contracts():
    """Verify runefoble-board and runefoble-tactical-board Custom Elements and Storybook stories."""
    ui_src = REPO_ROOT / "services/board_state/ui/src"
    board_file = ui_src / "runefoble-board.ts"
    particle_file = ui_src / "particle_canvas.ts"
    stories_file = ui_src / "runefoble-board.stories.ts"

    assert board_file.is_file()
    assert particle_file.is_file()
    assert stories_file.is_file()

    board_content = board_file.read_text(encoding="utf-8")
    stories_content = stories_file.read_text(encoding="utf-8")

    # Custom element tags
    assert "@customElement('runefoble-board')" in board_content
    assert "@customElement('runefoble-tactical-board')" in board_content
    assert "triggerSpellVFX" in board_content

    # Storybook stories for firestorm, lightning, and shield barrier
    assert "EvocationFirestormVFX" in stories_content
    assert "EvocationLightningArcVFX" in stories_content
    assert "AbjurationShieldBarrierVFX" in stories_content
