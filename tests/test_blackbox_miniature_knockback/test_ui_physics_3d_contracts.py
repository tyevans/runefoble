"""Blackbox UI contract and manifest discovery tests for Miniature Knockback Physics (TASK-0171).

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


def test_ui_manifest_frontdoor_contract(client: TestClient) -> None:
    """Verify board_state GET /ui/manifest frontdoor exposes table components."""
    resp = client.get("/ui/manifest")
    assert resp.status_code == 200, resp.text
    manifest = resp.json()

    assert manifest["service"] == "board_state"
    assert manifest["package"] == "@runefoble/board-state-ui"
    assert "runefoble-tabletop-3d" in manifest["components"]
    assert "runefoble-board" in manifest["components"]

    alias_resp = client.get("/board_state/ui/manifest")
    assert alias_resp.status_code == 200
    assert "runefoble-tabletop-3d" in alias_resp.json()["components"]


def test_manifest_file_matches_frontdoor_endpoint(client: TestClient) -> None:
    """Verify services/board_state/ui/manifest.json matches runtime endpoint response."""
    manifest_path = REPO_ROOT / "services/board_state/ui/manifest.json"
    assert manifest_path.is_file(), f"{manifest_path} must exist"
    file_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    api_data = client.get("/ui/manifest").json()

    assert file_data["service"] == api_data["service"]
    assert file_data["package"] == api_data["package"]
    assert file_data["components"] == api_data["components"]


def test_typescript_physics_3d_modules_and_line_limits() -> None:
    """Verify modular architecture, exports, and strict file length limits."""
    ui_dir = REPO_ROOT / "services/board_state/ui"

    physics_index = (ui_dir / "src/physics_3d/index.ts").read_text(encoding="utf-8")
    assert "knockback_solver" in physics_index
    assert "elevation_fall" in physics_index
    assert "grid_snapper" in physics_index

    # Check file length limits per specification
    files_to_check: dict[Path, int] = {
        ui_dir / "src/physics_3d/knockback_solver.ts": 140,
        ui_dir / "src/physics_3d/elevation_fall.ts": 140,
        ui_dir / "src/physics_3d/grid_snapper.ts": 120,
        ui_dir / "src/runefoble-knockback-3d.stories.ts": 130,
    }

    for file_path, limit in files_to_check.items():
        assert file_path.is_file(), f"{file_path} must exist"
        line_count = len(file_path.read_text(encoding="utf-8").splitlines())
        assert line_count <= limit, f"{file_path.name} exceeds limit: {line_count} > {limit}"


def test_physics_solver_contracts() -> None:
    """Verify mathematical functions, parameters, and return types in solvers."""
    ui_dir = REPO_ROOT / "services/board_state/ui/src/physics_3d"

    knockback_src = (ui_dir / "knockback_solver.ts").read_text(encoding="utf-8")
    for term in (
        "solveKnockbackTrajectory",
        "mass",
        "friction",
        "restitution",
        "reboundVector",
        "impactEnergy",
        "tiltX",
        "tiltY",
    ):
        assert term in knockback_src

    elevation_src = (ui_dir / "elevation_fall.ts").read_text(encoding="utf-8")
    for term in (
        "solveElevationFall",
        "gravity",
        "tiltDamping",
        "impactBounce",
        "recoveredUpright",
        "fallHeight",
        "tiltAngle",
    ):
        assert term in elevation_src

    snapper_src = (ui_dir / "grid_snapper.ts").read_text(encoding="utf-8")
    for term in (
        "snapMiniatureToGrid",
        "scheduleGridSnap",
        "dispatchGridSyncEvent",
        "syncedWithin50ms",
        "settledInMs",
        "50",
    ):
        assert term in snapper_src


def test_storybook_stories_definition() -> None:
    """Verify Storybook stories showcase bull-rush shoves, cliff drops, wall bounces, and theme switches."""
    stories_file = REPO_ROOT / "services/board_state/ui/src/runefoble-knockback-3d.stories.ts"
    assert stories_file.is_file()
    src = stories_file.read_text(encoding="utf-8")

    expected_stories = [
        "BullRushShove",
        "CliffDropFall",
        "WallBounceRebound",
        "LightThemeKnockback",
        "HighContrastKnockback",
    ]
    for story in expected_stories:
        assert story in src, f"Story {story} must be defined in {stories_file.name}"
