"""Blackbox tests for ephemeral decal decay, animation finished lifecycle, and particle contracts."""

from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi.testclient import TestClient


def test_ephemeral_decal_decay_over_two_rounds(
    client: TestClient, fireball_payload: dict[str, Any]
) -> None:
    """Verify ephemeral scorched earth decals decay and naturally fade after 2 rounds."""
    board_id = f"board-{uuid4().hex[:8]}"
    client.post("/api/v1/boards", json={"board_id": board_id, "cols": 10, "rows": 10})
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


def test_vfx_animation_finished_endpoint(client: TestClient) -> None:
    """Verify POST /api/v1/boards/{session_id}/vfx/finish persists and acknowledges completion."""
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


def test_ui_components_storybook_and_microfrontend_contracts(ui_src: Path) -> None:
    """Verify runefoble-board and runefoble-tactical-board Custom Elements and Storybook stories."""
    board_file = ui_src / "runefoble-board.ts"
    particle_file = ui_src / "particle_canvas.ts"
    stories_file = ui_src / "runefoble-board.stories.ts"

    assert board_file.is_file() and particle_file.is_file() and stories_file.is_file()
    board_content = board_file.read_text(encoding="utf-8")
    stories_content = stories_file.read_text(encoding="utf-8")

    assert "@customElement('runefoble-board')" in board_content
    assert "@customElement('runefoble-tactical-board')" in board_content
    assert "triggerSpellVFX" in board_content

    assert "EvocationFirestormVFX" in stories_content
    assert "EvocationLightningArcVFX" in stories_content
    assert "AbjurationShieldBarrierVFX" in stories_content


def test_particle_canvas_modular_decomposition_and_line_limits(ui_src: Path) -> None:
    """Verify TASK-0132 modular decomposition of particle canvas into projectiles and decals."""
    canvas_file = ui_src / "particle_canvas.ts"
    projectiles_file = ui_src / "particle_projectiles.ts"
    decals_file = ui_src / "particle_decals.ts"

    assert canvas_file.is_file() and projectiles_file.is_file() and decals_file.is_file()
    canvas_lines = len(canvas_file.read_text(encoding="utf-8").splitlines())
    proj_lines = len(projectiles_file.read_text(encoding="utf-8").splitlines())
    decal_lines = len(decals_file.read_text(encoding="utf-8").splitlines())

    assert canvas_lines < 260, f"particle_canvas.ts must be < 260 lines, got {canvas_lines}"
    assert proj_lines < 200, f"particle_projectiles.ts must be < 200 lines, got {proj_lines}"
    assert decal_lines < 200, f"particle_decals.ts must be < 200 lines, got {decal_lines}"

    proj_content = projectiles_file.read_text(encoding="utf-8")
    assert "class ProjectileManager" in proj_content
    assert "calculateParabolicTrajectory" in proj_content
    assert "hasProjectileCollided" in proj_content

    decal_content = decals_file.read_text(encoding="utf-8")
    assert "class DecalManager" in decal_content
    assert "calculateDecalOpacity" in decal_content
    assert "renderDecals2D" in decal_content
