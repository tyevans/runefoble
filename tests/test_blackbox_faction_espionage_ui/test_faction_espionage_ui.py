"""Blackbox TDD frontdoor test suite for Faction Espionage and Alert Feeds Microfrontend.

Governed by:
- ADR-0004: Lit + Vite Microfrontends with Storybook
- ADR-0012: CSS Custom Properties & Semantic Dark/Light Invariants
- ADR-0013: Modular Microfrontend Decomposition
- Hard Invariant 6: File length limit (< 500 lines)
- Hard Invariant 7: Blackbox TDD with Frontdoor Setup
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from the_watcher.main import app

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_the_watcher_ui_manifest_advertises_faction_espionage(client: TestClient) -> None:
    """Verify GET /ui/manifest frontdoor exposes runefoble-faction-espionage component."""
    for path in ["/ui/manifest", "/the-watcher/ui/manifest"]:
        resp = client.get(path)
        assert resp.status_code == 200, f"Failed at {path}"
        data = resp.json()
        assert data["service"] == "the_watcher"
        assert data["package"] == "@runefoble/the-watcher-ui"
        assert data["version"] == "0.1.0"
        assert "runefoble-faction-espionage" in data["components"]
        assert "runefoble-faction-radar" in data["components"]
        assert "runefoble-autonomous-dm" in data["components"]
        assert "runefoble-watcher-feed" in data["components"]


def test_manifest_file_matches_advertised_manifest() -> None:
    """Verify services/the_watcher/ui/manifest.json matches runtime advertising."""
    manifest_path = REPO_ROOT / "services/the_watcher/ui/manifest.json"
    assert manifest_path.is_file(), f"{manifest_path} must exist"

    manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest_data["service"] == "the_watcher"
    assert manifest_data["package"] == "@runefoble/the-watcher-ui"
    assert manifest_data["version"] == "0.1.0"
    assert "runefoble-faction-espionage" in manifest_data["components"]


def test_package_json_and_typescript_exports() -> None:
    """Verify UI package exports, index re-exports, and App Shell forwarding."""
    ui_dir = REPO_ROOT / "services/the_watcher/ui"

    pkg_json = json.loads((ui_dir / "package.json").read_text(encoding="utf-8"))
    assert pkg_json["name"] == "@runefoble/the-watcher-ui"
    assert "./runefoble-faction-espionage" in pkg_json["exports"]

    index_src = (ui_dir / "src/index.ts").read_text(encoding="utf-8")
    assert "runefoble-faction-espionage.ts" in index_src
    assert "runefoble-faction-espionage.styles.ts" in index_src

    forwarding_file = REPO_ROOT / "frontend/src/components/runefoble-faction-espionage.ts"
    assert forwarding_file.is_file()
    assert "@runefoble/the-watcher-ui" in forwarding_file.read_text(encoding="utf-8")


def test_typescript_element_source_and_custom_elements() -> None:
    """Verify component custom element registration, properties, and event emission."""
    comp_file = REPO_ROOT / "services/the_watcher/ui/src/runefoble-faction-espionage.ts"
    assert comp_file.is_file()
    comp_src = comp_file.read_text(encoding="utf-8")

    assert "@customElement('runefoble-faction-espionage')" in comp_src
    assert "class RunefobleFactionEspionage" in comp_src
    assert "alert-selected" in comp_src
    assert "dispatch-inspected" in comp_src
    assert "filter-changed" in comp_src

    assert "campaignId" in comp_src
    assert "alerts" in comp_src
    assert "intercepts" in comp_src
    assert "regionalAlerts" in comp_src
    assert "filterSeverity" in comp_src
    assert "isDm" in comp_src


def test_styles_definition_and_wcag_contrast_tokens() -> None:
    """Verify scoped CSS styles adhere to Bauhaus design tokens and contrast standards."""
    styles_file = REPO_ROOT / "services/the_watcher/ui/src/runefoble-faction-espionage.styles.ts"
    assert styles_file.is_file()
    styles_src = styles_file.read_text(encoding="utf-8")

    assert "espionageStyles" in styles_src
    assert "--rf-bg-surface" in styles_src
    assert "--rf-border-color" in styles_src
    assert "--rf-text-primary" in styles_src
    assert "--rf-text-secondary" in styles_src
    assert "--rf-color-accent" in styles_src
    assert "badge-critical" in styles_src
    assert "badge-high" in styles_src
    assert "badge-medium" in styles_src


def test_storybook_stories_definition() -> None:
    """Verify Storybook stories contain required test variants."""
    stories_file = REPO_ROOT / "services/the_watcher/ui/src/runefoble-faction-espionage.stories.ts"
    assert stories_file.is_file()
    content = stories_file.read_text(encoding="utf-8")

    assert "Default" in content
    assert "HighUrgencyAlerts" in content
    assert "InterceptedDispatches" in content
    assert "EmptyState" in content
    assert "DMPrivateBriefing" in content
    assert "runefoble-faction-espionage" in content


def test_file_length_invariants() -> None:
    """Verify file lengths strictly conform to modular microfrontend limits."""
    comp_lines = len(
        (REPO_ROOT / "services/the_watcher/ui/src/runefoble-faction-espionage.ts")
        .read_text(encoding="utf-8")
        .splitlines()
    )
    assert comp_lines < 150, f"Component file has {comp_lines} lines (must be < 150)"

    styles_lines = len(
        (REPO_ROOT / "services/the_watcher/ui/src/runefoble-faction-espionage.styles.ts")
        .read_text(encoding="utf-8")
        .splitlines()
    )
    assert styles_lines < 120, f"Styles file has {styles_lines} lines (must be < 120)"

    manifest_router_lines = len(
        (REPO_ROOT / "services/the_watcher/src/the_watcher/routers/ui_manifest.py")
        .read_text(encoding="utf-8")
        .splitlines()
    )
    assert manifest_router_lines < 80, (
        f"UI manifest router has {manifest_router_lines} lines (must be < 80)"
    )

    stories_lines = len(
        (REPO_ROOT / "services/the_watcher/ui/src/runefoble-faction-espionage.stories.ts")
        .read_text(encoding="utf-8")
        .splitlines()
    )
    assert stories_lines < 130, f"Stories file has {stories_lines} lines (must be < 130)"
