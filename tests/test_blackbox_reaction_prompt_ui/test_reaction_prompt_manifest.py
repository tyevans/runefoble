"""Manifest and microfrontend component delivery tests for Reaction Prompt UI (TASK-0158).

Governed by:
- ADR-0004: Lit Web Components and Storybook UI
- ADR-0012: Theming System and Accessibility Contrast Invariants
- ADR-0013: Microfrontend Architecture and Service Component Vendoring
- Hard Invariant 6: File length limit (< 500 lines)
- Hard Invariant 7: Blackbox TDD with Frontdoor Setup
"""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from .conftest import REPO_ROOT


def test_reaction_prompt_manifest_endpoint(client: TestClient) -> None:
    """Verify GET /ui/manifest frontdoor exposes reaction prompt and ready action card."""
    resp = client.get("/ui/manifest")
    assert resp.status_code == 200
    data = resp.json()
    assert data["service"] == "game_session"
    assert data["package"] == "@runefoble/game-session-ui"
    assert data["version"] == "0.1.0"
    assert "runefoble-combat-reaction-prompt" in data["components"]
    assert "runefoble-ready-action-card" in data["components"]

    # Test routed alias /game_session/ui/manifest
    alias_resp = client.get("/game_session/ui/manifest")
    assert alias_resp.status_code == 200
    alias_data = alias_resp.json()
    assert "runefoble-combat-reaction-prompt" in alias_data["components"]
    assert "runefoble-ready-action-card" in alias_data["components"]


def test_manifest_file_matches_advertised_manifest(client: TestClient) -> None:
    """Verify services/game_session/ui/manifest.json matches runtime advertising."""
    manifest_path = REPO_ROOT / "services/game_session/ui/manifest.json"
    assert manifest_path.is_file(), f"{manifest_path} must exist"
    manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    endpoint_data = client.get("/ui/manifest").json()
    assert manifest_data["service"] == endpoint_data["service"]
    assert manifest_data["package"] == endpoint_data["package"]
    assert "runefoble-combat-reaction-prompt" in manifest_data["components"]
    assert "runefoble-ready-action-card" in manifest_data["components"]


def test_typescript_element_source_and_custom_elements() -> None:
    """Verify UI package configuration, exports, and Custom Element decorators."""
    ui_dir = REPO_ROOT / "services/game_session/ui"
    pkg_json = json.loads((ui_dir / "package.json").read_text(encoding="utf-8"))
    assert pkg_json["name"] == "@runefoble/game-session-ui"
    assert "./runefoble-combat-reaction-prompt" in pkg_json["exports"]
    assert "./runefoble-combat-reaction-prompt.styles" in pkg_json["exports"]
    assert "./runefoble-ready-action-card" in pkg_json["exports"]

    assert (ui_dir / "tsconfig.json").is_file()
    index_src = (ui_dir / "src/index.ts").read_text(encoding="utf-8")
    assert "runefoble-combat-reaction-prompt" in index_src
    assert "runefoble-ready-action-card" in index_src

    prompt_src = (ui_dir / "src/runefoble-combat-reaction-prompt.ts").read_text(encoding="utf-8")
    assert "@customElement('runefoble-combat-reaction-prompt')" in prompt_src
    assert "class RunefobleCombatReactionPrompt" in prompt_src
    for term in (
        "reaction-resolved",
        "reaction-timeout",
        "secondsRemaining",
        "resolveOption",
        "decline",
    ):
        assert term in prompt_src

    card_src = (ui_dir / "src/runefoble-ready-action-card.ts").read_text(encoding="utf-8")
    assert "@customElement('runefoble-ready-action-card')" in card_src
    assert "class RunefobleReadyActionCard" in card_src
    for term in ("ready-action-registered", "ready-action-cancelled", "armAction", "disarmAction"):
        assert term in card_src

    styles_src = (ui_dir / "src/runefoble-combat-reaction-prompt.styles.ts").read_text(
        encoding="utf-8"
    )
    for token in ("--rf-accent-primary", "--rf-border-color", "--rf-shadow", "--rf-bg-surface"):
        assert token in styles_src


def test_storybook_stories_definition() -> None:
    """Verify Storybook stories include active countdown, urgent expiring, accepted, and expired states."""
    stories_file = (
        REPO_ROOT / "services/game_session/ui/src/runefoble-combat-reaction-prompt.stories.ts"
    )
    assert stories_file.is_file()
    content = stories_file.read_text(encoding="utf-8")
    expected_stories = (
        "ActiveCountdown",
        "UrgentExpiring",
        "TriggerAccepted",
        "TimeoutExpired",
        "ReadyActionCardUnarmed",
        "ReadyActionCardArmed",
        "runefoble-combat-reaction-prompt",
    )
    for story in expected_stories:
        assert story in content


def test_frontend_app_shell_forwarding_export() -> None:
    """Verify frontend/src/components/ re-exports the microfrontend per ADR-0013."""
    forwarding_file = REPO_ROOT / "frontend/src/components/runefoble-combat-reaction-prompt.ts"
    assert forwarding_file.is_file()
    assert "@runefoble/game-session-ui" in forwarding_file.read_text(encoding="utf-8")

    shell_index = REPO_ROOT / "frontend/src/index.ts"
    assert "runefoble-combat-reaction-prompt" in shell_index.read_text(encoding="utf-8")


def test_reaction_prompt_files_strictly_under_160_lines() -> None:
    """Verify all reaction prompt UI files strictly comply with <160 lines limit (Hard Invariant 6)."""
    ui_dir = REPO_ROOT / "services/game_session/ui/src"
    files = [
        (ui_dir / "runefoble-combat-reaction-prompt.ts", 150),
        (ui_dir / "runefoble-ready-action-card.ts", 130),
        (ui_dir / "runefoble-combat-reaction-prompt.styles.ts", 120),
        (ui_dir / "runefoble-combat-reaction-prompt.stories.ts", 140),
    ]
    for path, max_lines in files:
        assert path.is_file(), f"{path} must exist"
        lines = len(path.read_text(encoding="utf-8").splitlines())
        assert lines < max_lines, f"{path.name} has {lines} lines, exceeding limit of {max_lines}"
