"""Blackbox tests for Microfrontend Manifests and Component Contracts.

Verifies that each service bounded context vendors its own UI components, exposes
its microfrontend manifest through its public HTTP frontdoor (GET /ui/manifest),
and enforces package structure and component naming conventions.
"""

from pathlib import Path

import pytest
from starlette.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def board_client():
    from board_state.main import app

    return TestClient(app)


@pytest.fixture
def character_client():
    from character_sheet.main import app

    return TestClient(app)


@pytest.fixture
def session_client():
    from game_session.main import app

    return TestClient(app)


@pytest.fixture
def watcher_client():
    from the_watcher.main import app

    return TestClient(app)


@pytest.fixture
def voice_client():
    from voice_agent.main import app

    return TestClient(app)


@pytest.fixture
def campaign_client():
    from campaign_analytics.main import app

    return TestClient(app)


@pytest.fixture
def rules_client():
    from rules_compendium.main import app

    return TestClient(app)


@pytest.fixture
def lore_client():
    from campaign_lore.main import app

    return TestClient(app)


def test_board_state_ui_manifest_frontdoor(board_client):
    """Verify board_state service vendors its microfrontend via GET /ui/manifest."""
    response = board_client.get("/ui/manifest")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "board_state"
    assert data["package"] == "@runefoble/board-state-ui"
    assert "runefoble-board" in data["components"]
    assert "runefoble-map-uploader" in data["components"]


def test_character_sheet_ui_manifest_frontdoor(character_client):
    """Verify character_sheet service vendors its microfrontend via GET /ui/manifest."""
    response = character_client.get("/ui/manifest")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "character_sheet"
    assert data["package"] == "@runefoble/character-sheet-ui"
    assert "runefoble-character-card" in data["components"]
    assert "runefoble-absentee-recap" in data["components"]
    assert "runefoble-character-sheet" in data["components"]
    assert "runefoble-character-roster" in data["components"]
    assert "runefoble-character-builder-modal" in data["components"]


def test_game_session_ui_manifest_frontdoor(session_client):
    """Verify game_session service vendors its microfrontend via GET /ui/manifest."""
    response = session_client.get("/ui/manifest")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "game_session"
    assert data["package"] == "@runefoble/game-session-ui"
    assert "runefoble-initiative-tracker" in data["components"]
    assert "runefoble-dice-roller" in data["components"]
    assert "runefoble-spectator-view" in data["components"]
    assert "runefoble-combat-reaction-prompt" in data["components"]
    assert "runefoble-ready-action-card" in data["components"]
    assert "runefoble-campaign-dashboard" in data["components"]
    assert "runefoble-campaign-creator" in data["components"]
    assert "runefoble-campaign-members" in data["components"]


def test_the_watcher_ui_manifest_frontdoor(watcher_client):
    """Verify the_watcher service vendors its microfrontend via GET /ui/manifest."""
    response = watcher_client.get("/ui/manifest")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "the_watcher"
    assert data["package"] == "@runefoble/the-watcher-ui"
    assert "runefoble-watcher-feed" in data["components"]
    assert "runefoble-autonomous-dm" in data["components"]


def test_voice_agent_ui_manifest_frontdoor(voice_client):
    """Verify voice_agent service vendors its microfrontend via GET /ui/manifest."""
    response = voice_client.get("/ui/manifest")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "voice_agent"
    assert data["package"] == "@runefoble/voice-agent-ui"
    assert "runefoble-voice-controls" in data["components"]


def test_campaign_analytics_ui_manifest_frontdoor(campaign_client):
    """Verify campaign_analytics service vendors its microfrontend via GET /ui/manifest."""
    response = campaign_client.get("/ui/manifest")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "campaign-analytics"
    assert data["package"] == "@runefoble/campaign-analytics-ui"
    assert "runefoble-campaign-analytics" in data["components"]


def test_rules_compendium_ui_manifest_frontdoor(rules_client):
    """Verify rules_compendium service vendors its microfrontend via GET /ui/manifest."""
    response = rules_client.get("/ui/manifest")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "rules_compendium"
    assert data["package"] == "@runefoble/rules-compendium-ui"
    assert "runefoble-rules-compendium" in data["components"]
    assert "runefoble-rules-lookup" in data["components"]
    assert "runefoble-encounter-builder" in data["components"]


def test_campaign_lore_ui_manifest_frontdoor(lore_client):
    """Verify campaign_lore service vendors its microfrontends via GET /ui/manifest."""
    response = lore_client.get("/ui/manifest")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "campaign_lore"
    assert data["package"] == "@runefoble/campaign-lore-ui"
    assert "runefoble-west-marches-atlas" in data["components"]
    assert "runefoble-campaign-atlas" in data["components"]


def test_service_ui_package_integrity():
    """Verify that all service UI packages have package.json, tsconfig.json, and Lit elements."""
    expected_packages = [
        ("services/board_state/ui", "@runefoble/board-state-ui", "runefoble-board"),
        ("services/board_state/ui", "@runefoble/board-state-ui", "runefoble-map-uploader"),
        (
            "services/character_sheet/ui",
            "@runefoble/character-sheet-ui",
            "runefoble-character-card",
        ),
        (
            "services/character_sheet/ui",
            "@runefoble/character-sheet-ui",
            "runefoble-character-sheet",
        ),
        (
            "services/character_sheet/ui",
            "@runefoble/character-sheet-ui",
            "runefoble-character-roster",
        ),
        (
            "services/character_sheet/ui",
            "@runefoble/character-sheet-ui",
            "runefoble-character-builder-modal",
        ),
        ("services/game_session/ui", "@runefoble/game-session-ui", "runefoble-initiative-tracker"),
        ("services/the_watcher/ui", "@runefoble/the-watcher-ui", "runefoble-watcher-feed"),
        ("services/voice_agent/ui", "@runefoble/voice-agent-ui", "runefoble-voice-controls"),
        ("services/asset_forge/ui", "@runefoble/asset-forge-ui", "runefoble-asset-forge"),
        ("services/soundscape/ui", "@runefoble/soundscape-ui", "runefoble-soundscape-controls"),
        (
            "services/audience_studio/ui",
            "@runefoble/audience-studio-ui",
            "runefoble-audience-studio",
        ),
        (
            "services/campaign_analytics/ui",
            "@runefoble/campaign-analytics-ui",
            "runefoble-campaign-analytics",
        ),
        (
            "services/rules_compendium/ui",
            "@runefoble/rules-compendium-ui",
            "runefoble-rules-compendium",
        ),
        (
            "services/campaign_lore/ui",
            "@runefoble/campaign-lore-ui",
            "runefoble-west-marches-atlas",
        ),
    ]

    for rel_dir, pkg_name, elem_tag in expected_packages:
        pkg_path = REPO_ROOT / rel_dir / "package.json"
        assert pkg_path.is_file(), f"{pkg_path} must exist"
        content = pkg_path.read_text(encoding="utf-8")
        assert f'"name": "{pkg_name}"' in content

        tsconfig = REPO_ROOT / rel_dir / "tsconfig.json"
        assert tsconfig.is_file(), f"{tsconfig} must exist"

        index_file = REPO_ROOT / rel_dir / "src" / "index.ts"
        assert index_file.is_file(), f"{index_file} must exist"

        src_files = list((REPO_ROOT / rel_dir / "src").rglob("*.ts"))
        assert any(
            f"@customElement('{elem_tag}')" in f.read_text(encoding="utf-8") for f in src_files
        ), f"Custom element '{elem_tag}' not found in {rel_dir}/src"


def test_battlemap_uploader_microfrontend_frontdoor(board_client):
    """Verify battlemap asset uploader component integrity and Silo S3 upload frontdoor."""
    from gateway_api.main import app as gateway_app

    # 1. Manifest discovery frontdoor
    response = board_client.get("/ui/manifest")
    assert response.status_code == 200
    manifest = response.json()
    assert manifest["service"] == "board_state"
    assert manifest["package"] == "@runefoble/board-state-ui"
    assert "runefoble-map-uploader" in manifest["components"]

    # 2. Silo S3 asset upload frontdoor integration
    gateway_client = TestClient(gateway_app)
    sample_png = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06"
        b"\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01"
        b"\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    upload_res = gateway_client.post(
        "/api/v1/assets/upload",
        files={"file": ("crypt_dungeon_grid.png", sample_png, "image/png")},
        data={"owner_id": "gm-alex", "asset_type": "battlemap"},
    )
    assert upload_res.status_code == 200
    upload_data = upload_res.json()
    assert "asset_id" in upload_data
    assert "battlemaps/" in upload_data["object_key"]
    assert upload_data["content_type"] == "image/png"
    assert upload_data["owner_id"] == "gm-alex"
    assert "download_url" in upload_data

    # 3. Component code and event contract verification
    comp_file = REPO_ROOT / "services" / "board_state" / "ui" / "src" / "runefoble-map-uploader.ts"
    assert comp_file.is_file()
    code = comp_file.read_text(encoding="utf-8")
    assert "@customElement('runefoble-map-uploader')" in code
    assert "map-uploaded" in code
    assert "shroud-overlay" in code
    assert "uploadEndpoint" in code

    # 4. Interactive Storybook stories contract
    stories_file = (
        REPO_ROOT / "services" / "board_state" / "ui" / "src" / "runefoble-map-uploader.stories.ts"
    )
    assert stories_file.is_file()
    stories_code = stories_file.read_text(encoding="utf-8")
    assert "EmptyDropzone" in stories_code
    assert "UploadingProgress" in stories_code
    assert "AlignedMapPreview" in stories_code
    assert "FogOfWarMasked" in stories_code
