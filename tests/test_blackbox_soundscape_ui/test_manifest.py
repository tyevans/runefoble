"""Microfrontend manifest and component delivery tests for Soundscape UI (TASK-0154).

Governed by:
- ADR-0004: Lit Web Components and Storybook UI
- ADR-0013: Microfrontend Architecture and Service Component Vendoring
- Hard Invariant 6: File length limit (< 500 lines)
- Hard Invariant 7: Blackbox TDD with Frontdoor Setup
"""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from .conftest import REPO_ROOT


def test_soundscape_manifest_endpoint(client: TestClient) -> None:
    """Verify GET /ui/manifest frontdoor exposes correct microfrontend metadata."""
    resp = client.get("/ui/manifest")
    assert resp.status_code == 200
    data = resp.json()
    assert data["service"] == "soundscape"
    assert data["package"] == "@runefoble/soundscape-ui"
    assert data["version"] == "0.1.0"
    assert "runefoble-soundscape-controls" in data["components"]
    assert "runefoble-soundscape-controls" in data["tags"]
    assert any("runefoble-soundscape-controls.styles" in s for s in data["styles"])
    assert any("index.ts" in s for s in data["scripts"])


def test_manifest_file_matches_advertised_manifest(client: TestClient) -> None:
    """Verify services/soundscape/ui/manifest.json matches runtime advertising."""
    manifest_path = REPO_ROOT / "services/soundscape/ui/manifest.json"
    assert manifest_path.is_file(), f"{manifest_path} must exist"
    manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    endpoint_data = client.get("/ui/manifest").json()
    for field in ("service", "package", "components", "tags"):
        assert manifest_data[field] == endpoint_data[field]


def test_typescript_element_source_and_custom_elements() -> None:
    """Verify UI package configuration, exports, and Custom Element decorators."""
    ui_dir = REPO_ROOT / "services/soundscape/ui"
    pkg_json = json.loads((ui_dir / "package.json").read_text(encoding="utf-8"))
    assert pkg_json["name"] == "@runefoble/soundscape-ui"
    assert "./runefoble-soundscape-controls" in pkg_json["exports"]
    assert "./runefoble-soundscape-controls.styles" in pkg_json["exports"]
    assert (ui_dir / "tsconfig.json").is_file()
    assert (ui_dir / "src/index.ts").is_file()

    comp_src = (ui_dir / "src/runefoble-soundscape-controls.ts").read_text(encoding="utf-8")
    assert "@customElement('runefoble-soundscape-controls')" in comp_src
    assert "class RunefobleSoundscapeControls" in comp_src
    expected_terms = (
        "playEarcon",
        "triggerDucking",
        "stemVolumes",
        "thunder",
        "door_slam",
        "steel_clash",
        "roar",
        "soundscape-volume",
        "soundscape-mood",
        "soundscape-cue",
        "soundscape-duck",
        "soundscape-stem-volume",
    )
    for term in expected_terms:
        assert term in comp_src

    styles_src = (ui_dir / "src/runefoble-soundscape-controls.styles.ts").read_text(
        encoding="utf-8"
    )
    for prop in ("--rf-accent-primary", "--rf-border-color", "--rf-shadow"):
        assert prop in styles_src


def test_storybook_stories_definition() -> None:
    """Verify Storybook stories include QuietAmbient, HighTensionCombat, and ActiveFoleyPlayback."""
    stories_file = REPO_ROOT / "services/soundscape/ui/src/runefoble-soundscape-controls.stories.ts"
    assert stories_file.is_file()
    content = stories_file.read_text(encoding="utf-8")
    expected_stories = (
        "ExplorationDefault",
        "QuietAmbient",
        "CombatActive",
        "HighTensionCombat",
        "BossClimax",
        "ActiveFoleyPlayback",
        "VoiceDuckingActive",
        "runefoble-soundscape-controls",
    )
    for story in expected_stories:
        assert story in content


def test_frontend_app_shell_forwarding_export() -> None:
    """Verify frontend/src/components/ re-exports the microfrontend per ADR-0013."""
    forwarding_file = REPO_ROOT / "frontend/src/components/runefoble-soundscape-controls.ts"
    assert forwarding_file.is_file()
    assert "@runefoble/soundscape-ui" in forwarding_file.read_text(encoding="utf-8")

    shell_index = REPO_ROOT / "frontend/src/index.ts"
    assert "runefoble-soundscape-controls" in shell_index.read_text(encoding="utf-8")

    frontend_pkg = json.loads((REPO_ROOT / "frontend/package.json").read_text(encoding="utf-8"))
    assert "@runefoble/soundscape-ui" in frontend_pkg["dependencies"]
