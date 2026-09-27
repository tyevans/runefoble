"""Blackbox UI contract and manifest discovery tests for 3D Dice Tray (TASK-0170).

Governed by:
- ADR-0004: Lit Web Components and Storybook UI
- ADR-0012: Design System Theming and Accessibility Contrast Invariants
- ADR-0013: Microfrontend Architecture and Service Component Vendoring
- Hard Invariant 6: File length limit (< 500 lines)
- Hard Invariant 7: Blackbox TDD with Frontdoor Setup
"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from .conftest import REPO_ROOT


def test_ui_manifest_advertises_dice_tray_3d(client: TestClient) -> None:
    """Verify board_state GET /ui/manifest frontdoor exposes runefoble-dice-tray-3d."""
    resp = client.get("/ui/manifest")
    assert resp.status_code == 200, resp.text
    manifest = resp.json()

    assert manifest["service"] == "board_state"
    assert manifest["package"] == "@runefoble/board-state-ui"
    assert "runefoble-dice-tray-3d" in manifest["components"]
    assert "runefoble-dice-tray-3d" in manifest["tags"]
    assert "./src/runefoble-dice-tray-3d.styles.ts" in manifest["styles"]

    # Verify routed alias /board_state/ui/manifest
    alias_resp = client.get("/board_state/ui/manifest")
    assert alias_resp.status_code == 200
    assert "runefoble-dice-tray-3d" in alias_resp.json()["components"]


def test_manifest_file_matches_frontdoor_endpoint(client: TestClient) -> None:
    """Verify services/board_state/ui/manifest.json matches runtime endpoint response."""
    manifest_path = REPO_ROOT / "services/board_state/ui/manifest.json"
    assert manifest_path.is_file(), f"{manifest_path} must exist"
    file_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    api_data = client.get("/ui/manifest").json()

    assert file_data["service"] == api_data["service"]
    assert file_data["package"] == api_data["package"]
    assert "runefoble-dice-tray-3d" in file_data["components"]
    assert file_data["components"] == api_data["components"]


def test_typescript_physics_3d_modules_and_line_limits() -> None:
    """Verify modular architecture, exports, and strict file length limits (< 160 lines)."""
    ui_dir = REPO_ROOT / "services/board_state/ui"
    pkg_json = json.loads((ui_dir / "package.json").read_text(encoding="utf-8"))

    assert pkg_json["name"] == "@runefoble/board-state-ui"
    assert "./runefoble-dice-tray-3d" in pkg_json["exports"]
    assert "./runefoble-dice-tray-3d.styles" in pkg_json["exports"]

    index_src = (ui_dir / "src/index.ts").read_text(encoding="utf-8")
    assert "runefoble-dice-tray-3d" in index_src

    physics_index = (ui_dir / "src/physics_3d/index.ts").read_text(encoding="utf-8")
    assert "dice_models" in physics_index
    assert "tray_audio" in physics_index
    assert "dice_solver" in physics_index

    # Check file length limits
    files_to_check: dict[Path, int] = {
        ui_dir / "src/physics_3d/dice_models.ts": 140,
        ui_dir / "src/physics_3d/tray_audio.ts": 120,
        ui_dir / "src/physics_3d/dice_solver.ts": 140,
        ui_dir / "src/runefoble-dice-tray-3d.ts": 160,
        ui_dir / "src/runefoble-dice-tray-3d.styles.ts": 100,
        ui_dir / "src/runefoble-dice-tray-3d.stories.ts": 130,
    }

    for file_path, limit in files_to_check.items():
        assert file_path.is_file(), f"{file_path} must exist"
        line_count = len(file_path.read_text(encoding="utf-8").splitlines())
        assert line_count <= limit, f"{file_path.name} exceeds limit: {line_count} > {limit}"


def test_polyhedral_dice_models_and_solver_contracts() -> None:
    """Verify polyhedral geometries, audio synthesizer, and deterministic solver logic."""
    ui_dir = REPO_ROOT / "services/board_state/ui/src"

    models_src = (ui_dir / "physics_3d/dice_models.ts").read_text(encoding="utf-8")
    for die in ("d4", "d6", "d8", "d10", "d12", "d20"):
        assert die in models_src
    for term in ("restitution", "friction", "getDiceColors", "getPolyhedralVertices"):
        assert term in models_src

    audio_src = (ui_dir / "physics_3d/tray_audio.ts").read_text(encoding="utf-8")
    for term in ("DiceTrayAudio", "playImpact", "playSettle", "AudioContext", "filter"):
        assert term in audio_src

    solver_src = (ui_dir / "physics_3d/dice_solver.ts").read_text(encoding="utf-8")
    for term in (
        "solveDeterministicToss",
        "verifyCryptographicAlignment",
        "bounces",
        "trajectory",
        "collisions",
    ):
        assert term in solver_src

    comp_src = (ui_dir / "runefoble-dice-tray-3d.ts").read_text(encoding="utf-8")
    assert "@customElement('runefoble-dice-tray-3d')" in comp_src
    assert "class RunefobleDiceTray3D" in comp_src
    for evt in ("dice-rolled", "dice-settled", "tray-audio-played"):
        assert evt in comp_src


def test_storybook_stories_definition() -> None:
    """Verify Storybook stories showcase multi-dice, ricochets, sounds, and themes."""
    stories_file = REPO_ROOT / "services/board_state/ui/src/runefoble-dice-tray-3d.stories.ts"
    assert stories_file.is_file()
    src = stories_file.read_text(encoding="utf-8")

    expected_stories = [
        "CriticalHitD20",
        "MultiDiceThrow",
        "BoundaryWallBounces",
        "LightThemeTray",
        "HighContrastTray",
    ]
    for story in expected_stories:
        assert story in src, f"Story {story} must be defined in {stories_file.name}"
