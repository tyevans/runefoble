"""Blackbox TDD frontdoor test suite for Session Lobby & Readiness UI.

Part of TASK-0212 / PRD-0023 / US-0065.
Governed by:
- ADR-0004: Lit Web Components and Storybook UI
- ADR-0012: Design System Theming and Bauhaus Modernism
- ADR-0013: Microfrontend Architecture and Service Component Vendoring
- Hard Invariant 6: File length limit (< 260 lines for component, < 500 lines overall)
- Hard Invariant 7: Blackbox TDD with frontdoor setup
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from game_session.main import app as session_app

REPO_ROOT = Path(__file__).resolve().parent.parent
UI_DIR = REPO_ROOT / "services" / "game_session" / "ui"
LOBBY_DIR = UI_DIR / "src" / "lobby"


@pytest.fixture
def client() -> TestClient:
    return TestClient(session_app)


# ---------------------------------------------------------------------------
# 1. Microfrontend Manifest & Package Structure Integrity
# ---------------------------------------------------------------------------


def test_session_lobby_manifest_frontdoor(client: TestClient) -> None:
    """Verify game_session service advertises runefoble-session-lobby via GET /ui/manifest."""
    response = client.get("/ui/manifest")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "game_session"
    assert data["package"] == "@runefoble/game-session-ui"
    assert data["version"] == "0.1.0"
    assert "runefoble-session-lobby" in data["components"]

    # Also test routed alias
    alias_res = client.get("/game_session/ui/manifest")
    assert alias_res.status_code == 200
    alias_data = alias_res.json()
    assert "runefoble-session-lobby" in alias_data["components"]


def test_manifest_file_matches_advertised_manifest() -> None:
    """Verify services/game_session/ui/manifest.json contains runefoble-session-lobby."""
    manifest_path = UI_DIR / "manifest.json"
    assert manifest_path.is_file(), f"{manifest_path} must exist"

    manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest_data["service"] == "game_session"
    assert manifest_data["package"] == "@runefoble/game-session-ui"
    assert "runefoble-session-lobby" in manifest_data["components"]


def test_session_lobby_package_exports() -> None:
    """Verify UI package configuration, exports, and re-exports in index.ts."""
    pkg_json = json.loads((UI_DIR / "package.json").read_text(encoding="utf-8"))
    assert pkg_json["name"] == "@runefoble/game-session-ui"
    assert "./lobby" in pkg_json["exports"]
    assert "./lobby/session-lobby" in pkg_json["exports"]
    assert "./lobby/styles" in pkg_json["exports"]

    index_ts = (UI_DIR / "src" / "index.ts").read_text(encoding="utf-8")
    assert "./lobby/index.ts" in index_ts

    lobby_index = (LOBBY_DIR / "index.ts").read_text(encoding="utf-8")
    assert "runefoble-session-lobby.ts" in lobby_index
    assert "runefoble-session-lobby.styles.ts" in lobby_index
    assert "types.ts" in lobby_index


# ---------------------------------------------------------------------------
# 2. Session Lobby Component Contracts & UI Invariants
# ---------------------------------------------------------------------------


def test_session_lobby_component_contracts() -> None:
    """Verify runefoble-session-lobby fulfills US-0065 and TASK-0212 requirements."""
    lobby_file = LOBBY_DIR / "runefoble-session-lobby.ts"
    assert lobby_file.is_file()

    src = lobby_file.read_text(encoding="utf-8")

    # Custom element registration and class
    assert "@customElement('runefoble-session-lobby')" in src
    assert "class RunefobleSessionLobby" in src

    # Properties
    assert "sessionId" in src
    assert "campaignId" in src
    assert "sessionTitle" in src
    assert "currentUserId" in src
    assert "participants" in src
    assert "availableCharacters" in src
    assert "isDm" in src
    assert "canLaunch" in src

    # Participant roster & UI elements
    assert "participants-grid" in src
    assert "participant-card" in src
    assert "avatar-wrap" in src
    assert "presence-dot" in src
    assert "badge-readiness" in src
    assert "character-card-preview" in src
    assert "character-dropdown" in src

    # Absentee & Readiness controls
    assert "checkbox-ready" in src
    assert "checkbox-absent" in src
    assert "AI Stand-In" in src
    assert "Ready to Play" in src

    # DM launch controls
    assert "btn-launch" in src
    assert "Launch Session" in src
    assert "readiness-summary-text" in src

    # Custom Events dispatched
    assert "'launch-session'" in src
    assert "'select-character'" in src
    assert "'toggle-readiness'" in src
    assert "'toggle-stand-in'" in src


def test_session_lobby_types_contracts() -> None:
    """Verify types.ts defines required data structures and readiness calculation."""
    types_file = LOBBY_DIR / "types.ts"
    assert types_file.is_file()

    src = types_file.read_text(encoding="utf-8")
    assert "interface LobbyParticipant" in src
    assert "interface LobbyCharacterOption" in src
    assert "interface ReadinessSummary" in src
    assert "interface LaunchSessionEventDetail" in src
    assert "interface SelectCharacterEventDetail" in src
    assert "interface ToggleReadinessEventDetail" in src
    assert "interface ToggleStandInEventDetail" in src
    assert "function computeReadinessSummary" in src


# ---------------------------------------------------------------------------
# 3. Design Tokens & Zero Hex Literals Invariant (ADR-0012)
# ---------------------------------------------------------------------------


def test_zero_hardcoded_hexes_in_session_lobby_styles() -> None:
    """Verify session lobby styles consume --rf-* tokens with zero hardcoded hex literals."""
    hex_pattern = re.compile(r"#[0-9a-fA-F]{3,8}")

    styles_file = LOBBY_DIR / "runefoble-session-lobby.styles.ts"
    assert styles_file.is_file()

    css_content = styles_file.read_text(encoding="utf-8")
    hexes_found = hex_pattern.findall(css_content)
    assert not hexes_found, f"Found hardcoded hex literals in lobby styles: {hexes_found}"

    # Consumes Bauhaus tokens
    for token in [
        "--rf-border-color",
        "--rf-shadow",
        "--rf-text-primary",
        "--rf-accent-primary",
        "--rf-bg-surface",
    ]:
        assert token in css_content, f"Expected {token} in lobby styles"


# ---------------------------------------------------------------------------
# 4. File Length Limits (< 260 lines DoD, < 500 lines Hard Invariant 6)
# ---------------------------------------------------------------------------


def test_session_lobby_files_line_counts() -> None:
    """Verify files comply with line count constraints (<260 lines for component, <500 lines overall)."""
    component_file = LOBBY_DIR / "runefoble-session-lobby.ts"
    component_lines = len(component_file.read_text(encoding="utf-8").splitlines())
    assert component_lines < 260, (
        f"runefoble-session-lobby.ts has {component_lines} lines (must be < 260 lines per DoD)"
    )

    for p in LOBBY_DIR.glob("*.ts"):
        line_count = len(p.read_text(encoding="utf-8").splitlines())
        assert line_count < 500, f"{p.name} exceeds 500 line invariant with {line_count} lines"


# ---------------------------------------------------------------------------
# 5. Storybook Stories
# ---------------------------------------------------------------------------


def test_session_lobby_storybook_stories_exist() -> None:
    """Verify Storybook stories exist for session lobby with required states."""
    stories_file = LOBBY_DIR / "runefoble-session-lobby.stories.ts"
    assert stories_file.is_file()

    stories_content = stories_file.read_text(encoding="utf-8")
    assert "DmViewAllReady" in stories_content
    assert "DmViewWithAbsentStandIn" in stories_content
    assert "PlayerViewUnready" in stories_content
    assert "PlayerViewReady" in stories_content
    assert "EmptyLobby" in stories_content
