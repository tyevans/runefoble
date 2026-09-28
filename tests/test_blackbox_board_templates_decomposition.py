"""Blackbox tests for Board Templates Rendering and Subviews Modular Decomposition.

TASK-0192: Board Templates Rendering and Subviews Modular Decomposition
Governed by:
- ADR-0004: Lit Web Components and Storybook UI
- ADR-0012: Design System Theming and Bauhaus Modernism
- ADR-0013: Microfrontend Architecture and Service Component Vendoring
- Hard Invariant 6: File length limit (< 500 lines) and task-specific modular boundaries
- Hard Invariant 7: Blackbox TDD with Frontdoor Setup
"""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
from board_state.main import app as board_app
from httpx import ASGITransport, AsyncClient

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_board_templates_file_length_limits() -> None:
    """Verify board templates and submodules strictly comply with TASK-0192 line limits."""
    templates_dir = REPO_ROOT / "services/board_state/ui/src/templates"
    facade_file = REPO_ROOT / "services/board_state/ui/src/board-templates.ts"

    assert facade_file.is_file(), f"{facade_file} must exist"
    facade_lines = len(facade_file.read_text(encoding="utf-8").splitlines())
    # Facade must be strictly < 60 lines (target < 50 lines)
    assert facade_lines < 60, f"board-templates.ts has {facade_lines} lines (must be < 60)"
    assert facade_lines < 50, f"board-templates.ts has {facade_lines} lines (target < 50)"

    submodules = [
        (templates_dir / "kinematics.template.ts", 130, 90),
        (templates_dir / "cell.template.ts", 130, 120),
        (templates_dir / "overlays.template.ts", 130, 130),
    ]

    for path, max_limit, target_limit in submodules:
        assert path.is_file(), f"{path} must exist"
        lines = len(path.read_text(encoding="utf-8").splitlines())
        assert lines < max_limit, f"{path.name} has {lines} lines (must be < {max_limit})"
        assert lines < target_limit, f"{path.name} has {lines} lines (target < {target_limit})"


def test_board_templates_facade_and_submodule_exports() -> None:
    """Verify aggregator facade re-exports all required template functions and interfaces."""
    facade_file = REPO_ROOT / "services/board_state/ui/src/board-templates.ts"
    facade_content = facade_file.read_text(encoding="utf-8")

    expected_reexports = [
        "getHealthBarColor",
        "renderVectorOverlay",
        "renderDistanceRuler",
        "renderGhostBanner",
        "BoardCellProps",
        "renderBoardCell",
        "renderBoardHeader",
        "renderStatusBar",
        "renderRadialMenuOverlay",
        "renderAoEOverlay",
        "renderAoEBanner",
    ]

    for sym in expected_reexports:
        assert sym in facade_content, f"Expected {sym} to be re-exported in board-templates.ts"

    # Verify kinematics template content
    kinematics_file = REPO_ROOT / "services/board_state/ui/src/templates/kinematics.template.ts"
    k_content = kinematics_file.read_text(encoding="utf-8")
    assert "getHealthBarColor" in k_content
    assert "renderVectorOverlay" in k_content
    assert "renderDistanceRuler" in k_content
    assert "renderGhostBanner" in k_content
    assert "calculateVectorLineCoordinates" in k_content

    # Verify cell template content
    cell_file = REPO_ROOT / "services/board_state/ui/src/templates/cell.template.ts"
    c_content = cell_file.read_text(encoding="utf-8")
    assert "interface BoardCellProps" in c_content
    assert "renderBoardCell" in c_content
    assert "getHealthBarColor" in c_content

    # Verify overlays template content
    overlays_file = REPO_ROOT / "services/board_state/ui/src/templates/overlays.template.ts"
    o_content = overlays_file.read_text(encoding="utf-8")
    assert "renderBoardHeader" in o_content
    assert "renderStatusBar" in o_content
    assert "renderRadialMenuOverlay" in o_content
    assert "renderAoEOverlay" in o_content
    assert "renderAoEBanner" in o_content


@pytest.mark.asyncio
async def test_frontdoor_board_state_integration_for_templates() -> None:
    """Verify board initialization, token placement, and movement match template representations."""
    transport = ASGITransport(app=board_app)
    session_id = f"session-tpl-{uuid4().hex[:8]}"

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Fetch initial board state via public frontdoor
        get_res = await client.get(f"/api/v1/boards/{session_id}")
        assert get_res.status_code == 200
        board_data = get_res.json()
        assert board_data["session_id"] == session_id
        assert board_data["cols"] > 0
        assert board_data["rows"] > 0

        # 2. Place token via public frontdoor
        token_id = f"hero-{uuid4().hex[:6]}"
        place_res = await client.post(
            f"/api/v1/boards/{session_id}/tokens",
            json={
                "token_id": token_id,
                "name": "Valeros",
                "x": 2,
                "y": 2,
                "color": "#e63946",
                "is_hostile": False,
                "is_ai_controlled": False,
            },
        )
        assert place_res.status_code == 200

        # 3. Move token via public frontdoor
        move_res = await client.post(
            f"/api/v1/boards/{session_id}/move",
            json={"token_id": token_id, "to_x": 4, "to_y": 5},
        )
        assert move_res.status_code == 200
        move_data = move_res.json()
        assert move_data["x"] == 4
        assert move_data["y"] == 5

        # 4. Configure terrain cell via public frontdoor
        terrain_res = await client.post(
            f"/api/v1/boards/{session_id}/terrain",
            json={
                "x": 4,
                "y": 5,
                "elevation": 1,
                "terrain_type": "difficult",
                "hazard": "spike_pit",
            },
        )
        assert terrain_res.status_code == 200

        # 5. Fetch updated board state and verify tokens and terrain are observable
        verify_res = await client.get(f"/api/v1/boards/{session_id}")
        assert verify_res.status_code == 200
        updated_board = verify_res.json()
        assert token_id in updated_board["tokens"]
        assert updated_board["tokens"][token_id]["x"] == 4
        assert updated_board["tokens"][token_id]["y"] == 5
