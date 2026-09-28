"""Blackbox tests for Board State Radial Menu Glyphs and Styles Decomposition.

TASK-0201: Board State Radial Menu Glyphs and Styles Modular Decomposition
Governed by:
- ADR-0004: Frontend Visualizer & Lit Component Architecture
- ADR-0012: Theming Tokens & Bauhaus Design System
- ADR-0013: Microfrontend Bounded Context Architecture
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


def test_radial_menu_file_length_limits() -> None:
    """Verify radial menu component and submodules strictly comply with TASK-0201 line limits."""
    radial_dir = REPO_ROOT / "services/board_state/ui/src/radial"
    controller_file = REPO_ROOT / "services/board_state/ui/src/radial_menu.ts"

    assert controller_file.is_file(), f"{controller_file} must exist"
    controller_lines = len(controller_file.read_text(encoding="utf-8").splitlines())
    assert controller_lines < 110, (
        f"radial_menu.ts has {controller_lines} lines (must be strictly < 110)"
    )
    assert controller_lines < 100, f"radial_menu.ts has {controller_lines} lines (target < 100)"

    submodules = [
        (radial_dir / "radial_menu.styles.ts", 110, 90),
        (radial_dir / "radial_glyphs.ts", 110, 100),
        (radial_dir / "radial_wedge.ts", 110, 90),
        (radial_dir / "index.ts", 110, 50),
    ]

    for path, max_limit, target_limit in submodules:
        assert path.is_file(), f"{path} must exist"
        lines = len(path.read_text(encoding="utf-8").splitlines())
        assert lines < max_limit, f"{path.name} has {lines} lines (must be strictly < {max_limit})"
        assert lines < target_limit, f"{path.name} has {lines} lines (target < {target_limit})"


def test_radial_menu_exports_and_submodule_structure() -> None:
    """Verify radial_menu.ts and submodules export required constants, types, and functions."""
    controller_file = REPO_ROOT / "services/board_state/ui/src/radial_menu.ts"
    controller_content = controller_file.read_text(encoding="utf-8")

    assert "@customElement('runefoble-radial-menu')" in controller_content
    assert "class RunefobleRadialMenu extends LitElement" in controller_content
    assert "export * from './radial/index.ts'" in controller_content
    assert "'runefoble-radial-menu': RunefobleRadialMenu" in controller_content

    # Verify styles submodule
    styles_file = REPO_ROOT / "services/board_state/ui/src/radial/radial_menu.styles.ts"
    styles_content = styles_file.read_text(encoding="utf-8")
    assert "export const radialMenuStyles = css`" in styles_content
    assert ".radial-container" in styles_content
    assert ".action-wedge" in styles_content
    assert ".center-button" in styles_content

    # Verify glyphs submodule
    glyphs_file = REPO_ROOT / "services/board_state/ui/src/radial/radial_glyphs.ts"
    glyphs_content = glyphs_file.read_text(encoding="utf-8")
    assert "export function renderBauhausGlyph" in glyphs_content
    for action in ["attack", "dash", "disengage", "dodge", "cast"]:
        assert f"case '{action}':" in glyphs_content

    # Verify wedge submodule
    wedge_file = REPO_ROOT / "services/board_state/ui/src/radial/radial_wedge.ts"
    wedge_content = wedge_file.read_text(encoding="utf-8")
    assert "export const RADIAL_ACTIONS" in wedge_content
    assert "export function polarToCartesian" in wedge_content
    assert "export function describeArc" in wedge_content
    assert "export function calculateWedgePosition" in wedge_content
    assert "export function renderWedge" in wedge_content


@pytest.mark.asyncio
async def test_frontdoor_radial_actions_execution() -> None:
    """Verify all 5 radial menu actions execute successfully via public frontdoor HTTP routes."""
    transport = ASGITransport(app=board_app)
    session_id = f"radial-sess-{uuid4().hex[:8]}"

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Initialize board
        init_res = await client.get(f"/api/v1/boards/{session_id}")
        assert init_res.status_code == 200

        # 2. Place active combatant token
        token_id = f"hero-{uuid4().hex[:6]}"
        place_res = await client.post(
            f"/api/v1/boards/{session_id}/tokens",
            json={
                "token_id": token_id,
                "name": "Valeros",
                "x": 3,
                "y": 3,
                "color": "#e63946",
                "is_hostile": False,
                "is_ai_controlled": False,
            },
        )
        assert place_res.status_code == 200

        # 3. Test execution for all 5 radial actions
        actions = ["attack", "dash", "disengage", "dodge", "cast"]
        for act in actions:
            act_res = await client.post(
                f"/api/v1/boards/{session_id}/tokens/{token_id}/action",
                json={
                    "action": act,
                    "initiated_by": "player",
                    "details": {"source": "radial_dial"},
                },
            )
            assert act_res.status_code == 200, f"Action '{act}' failed with: {act_res.text}"
            act_data = act_res.json()
            assert act_data["token_id"] == token_id
            assert act_data["action"] == act
            assert act_data["status"] == "executed"
            assert f"Action '{act}' successfully executed" in act_data["message"]
