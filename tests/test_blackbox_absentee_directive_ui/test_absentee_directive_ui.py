"""Blackbox TDD frontdoor test suite for Absentee Mobile Directive and Remote Voting Microfrontend.

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


def test_the_watcher_ui_manifest_advertises_absentee_components(client: TestClient) -> None:
    """Verify GET /ui/manifest frontdoor exposes absentee directive and vote card."""
    for path in ["/ui/manifest", "/the-watcher/ui/manifest"]:
        resp = client.get(path)
        assert resp.status_code == 200, f"Failed at {path}"
        data = resp.json()
        assert data["service"] == "the_watcher"
        assert data["package"] == "@runefoble/the-watcher-ui"
        assert data["version"] == "0.1.0"
        assert "runefoble-absentee-directive" in data["components"]
        assert "runefoble-absentee-vote-card" in data["components"]
        assert "runefoble-absentee-directive" in data["tags"]
        assert "runefoble-absentee-vote-card" in data["tags"]


def test_manifest_file_matches_advertised_manifest() -> None:
    """Verify services/the_watcher/ui/manifest.json matches runtime advertising."""
    manifest_path = REPO_ROOT / "services/the_watcher/ui/manifest.json"
    assert manifest_path.is_file(), f"{manifest_path} must exist"

    manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest_data["service"] == "the_watcher"
    assert manifest_data["package"] == "@runefoble/the-watcher-ui"
    assert manifest_data["version"] == "0.1.0"
    assert "runefoble-absentee-directive" in manifest_data["components"]
    assert "runefoble-absentee-vote-card" in manifest_data["components"]


def test_package_json_and_typescript_exports() -> None:
    """Verify UI package exports, index re-exports, and App Shell forwarding."""
    ui_dir = REPO_ROOT / "services/the_watcher/ui"

    pkg_json = json.loads((ui_dir / "package.json").read_text(encoding="utf-8"))
    assert pkg_json["name"] == "@runefoble/the-watcher-ui"
    assert "./runefoble-absentee-directive" in pkg_json["exports"]
    assert "./runefoble-absentee-vote-card" in pkg_json["exports"]

    index_src = (ui_dir / "src/index.ts").read_text(encoding="utf-8")
    assert "runefoble-absentee-directive.ts" in index_src
    assert "runefoble-absentee-directive.styles.ts" in index_src
    assert "runefoble-absentee-vote-card.ts" in index_src

    forwarding_directive = REPO_ROOT / "frontend/src/components/runefoble-absentee-directive.ts"
    assert forwarding_directive.is_file()
    assert "@runefoble/the-watcher-ui" in forwarding_directive.read_text(encoding="utf-8")

    forwarding_vote = REPO_ROOT / "frontend/src/components/runefoble-absentee-vote-card.ts"
    assert forwarding_vote.is_file()
    assert "@runefoble/the-watcher-ui" in forwarding_vote.read_text(encoding="utf-8")


def test_directive_element_source_and_custom_elements() -> None:
    """Verify directive component custom element registration, properties, and event emission."""
    comp_file = REPO_ROOT / "services/the_watcher/ui/src/runefoble-absentee-directive.ts"
    assert comp_file.is_file()
    comp_src = comp_file.read_text(encoding="utf-8")

    assert "@customElement('runefoble-absentee-directive')" in comp_src
    assert "class RunefobleAbsenteeDirective" in comp_src
    assert "directive-changed" in comp_src
    assert "stance-selected" in comp_src
    assert "haptic-pulse" in comp_src

    assert "characterName" in comp_src
    assert "currentStance" in comp_src
    assert "standInActive" in comp_src
    assert "penalties" in comp_src
    assert "activePoll" in comp_src
    assert "hapticFeedbackEnabled" in comp_src

    assert "defensive" in comp_src
    assert "cautious" in comp_src
    assert "heroic" in comp_src


def test_vote_card_element_source_and_haptics() -> None:
    """Verify vote card custom element, decision polls, and haptic pulse feedback."""
    vote_file = REPO_ROOT / "services/the_watcher/ui/src/runefoble-absentee-vote-card.ts"
    assert vote_file.is_file()
    vote_src = vote_file.read_text(encoding="utf-8")

    assert "@customElement('runefoble-absentee-vote-card')" in vote_src
    assert "class RunefobleAbsenteeVoteCard" in vote_src
    assert "vote-cast" in vote_src
    assert "haptic-pulse" in vote_src
    assert "navigator.vibrate" in vote_src
    assert "poll" in vote_src
    assert "hasVoted" in vote_src


def test_styles_definition_and_wcag_contrast_tokens() -> None:
    """Verify scoped CSS styles adhere to Bauhaus design tokens and touch accessibility."""
    styles_file = REPO_ROOT / "services/the_watcher/ui/src/runefoble-absentee-directive.styles.ts"
    assert styles_file.is_file()
    styles_src = styles_file.read_text(encoding="utf-8")

    assert "absenteeDirectiveStyles" in styles_src
    assert "--rf-bg-surface" in styles_src
    assert "--rf-border-color" in styles_src
    assert "--rf-text-primary" in styles_src
    assert "--rf-text-secondary" in styles_src
    assert "--rf-color-accent" in styles_src
    assert "min-height: 60px" in styles_src or "min-height: 48px" in styles_src
    assert "min-width: 44px" in styles_src


def test_storybook_stories_definition() -> None:
    """Verify Storybook stories contain required touch and posture scenarios."""
    stories_file = REPO_ROOT / "services/the_watcher/ui/src/runefoble-absentee-directive.stories.ts"
    assert stories_file.is_file()
    content = stories_file.read_text(encoding="utf-8")

    assert "Default" in content
    assert "CautiousHeroic" in content
    assert "AggressivePosture" in content
    assert "WithoutActivePoll" in content
    assert "LightThemePreview" in content
    assert "runefoble-absentee-directive" in content


def test_file_length_invariants() -> None:
    """Verify all component files strictly conform to modular microfrontend limits."""
    comp_lines = len(
        (REPO_ROOT / "services/the_watcher/ui/src/runefoble-absentee-directive.ts")
        .read_text(encoding="utf-8")
        .splitlines()
    )
    assert comp_lines < 150, f"Component file has {comp_lines} lines (must be < 150)"

    vote_lines = len(
        (REPO_ROOT / "services/the_watcher/ui/src/runefoble-absentee-vote-card.ts")
        .read_text(encoding="utf-8")
        .splitlines()
    )
    assert vote_lines < 130, f"Vote card file has {vote_lines} lines (must be < 130)"

    styles_lines = len(
        (REPO_ROOT / "services/the_watcher/ui/src/runefoble-absentee-directive.styles.ts")
        .read_text(encoding="utf-8")
        .splitlines()
    )
    assert styles_lines < 110, f"Styles file has {styles_lines} lines (must be < 110)"

    stories_lines = len(
        (REPO_ROOT / "services/the_watcher/ui/src/runefoble-absentee-directive.stories.ts")
        .read_text(encoding="utf-8")
        .splitlines()
    )
    assert stories_lines < 120, f"Stories file has {stories_lines} lines (must be < 120)"

    # Hard Invariant 6 and ADR-0013 check across all new UI files
    for name, lines in [
        ("directive", comp_lines),
        ("vote_card", vote_lines),
        ("styles", styles_lines),
        ("stories", stories_lines),
    ]:
        assert lines < 160, f"{name} file has {lines} lines (must be < 160)"
