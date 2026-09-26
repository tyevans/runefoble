"""Blackbox frontdoor tests for decomposed battlemap uploader and tactical subviews.

Verifies TASK-0078 decomposition of runefoble-map-uploader into:
- runefoble-map-dropzone.ts (< 130 lines)
- runefoble-map-grid-config.ts (< 140 lines)
- runefoble-map-uploader.ts (< 120 lines)
Conforms to Hard Invariant 6 (< 500 lines per file) and Hard Invariant 7 (Blackbox TDD).
"""

from pathlib import Path

import pytest
from starlette.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def board_client():
    from board_state.main import app

    return TestClient(app)


def test_board_state_ui_manifest_frontdoor(board_client):
    """Verify board_state microfrontend manifest discovers battlemap uploader."""
    response = board_client.get("/ui/manifest")
    assert response.status_code == 200
    manifest = response.json()
    assert manifest["service"] == "board_state"
    assert manifest["package"] == "@runefoble/board-state-ui"
    assert "runefoble-map-uploader" in manifest["components"]
    assert "runefoble-board" in manifest["components"]


def test_battlemap_uploader_modular_decomposition_integrity():
    """Verify runefoble-map-uploader and its subviews satisfy DoD file length limits and event contracts."""
    ui_src = REPO_ROOT / "services" / "board_state" / "ui" / "src"

    dropzone_file = ui_src / "runefoble-map-dropzone.ts"
    grid_config_file = ui_src / "runefoble-map-grid-config.ts"
    uploader_file = ui_src / "runefoble-map-uploader.ts"
    index_file = ui_src / "index.ts"

    assert dropzone_file.is_file(), "runefoble-map-dropzone.ts must exist"
    assert grid_config_file.is_file(), "runefoble-map-grid-config.ts must exist"
    assert uploader_file.is_file(), "runefoble-map-uploader.ts must exist"
    assert index_file.is_file(), "index.ts must exist"

    dropzone_code = dropzone_file.read_text(encoding="utf-8")
    grid_config_code = grid_config_file.read_text(encoding="utf-8")
    uploader_code = uploader_file.read_text(encoding="utf-8")
    index_code = index_file.read_text(encoding="utf-8")

    # Strict file length limits (< 150 lines per DoD)
    dropzone_lines = len(dropzone_code.splitlines())
    grid_config_lines = len(grid_config_code.splitlines())
    uploader_lines = len(uploader_code.splitlines())

    assert dropzone_lines < 150, (
        f"runefoble-map-dropzone.ts has {dropzone_lines} lines (expected < 150)"
    )
    assert grid_config_lines < 150, (
        f"runefoble-map-grid-config.ts has {grid_config_lines} lines (expected < 150)"
    )
    assert uploader_lines < 150, (
        f"runefoble-map-uploader.ts has {uploader_lines} lines (expected < 150)"
    )

    # Subcomponent target limits
    assert dropzone_lines < 130, (
        f"runefoble-map-dropzone.ts has {dropzone_lines} lines (target < 130)"
    )
    assert grid_config_lines < 140, (
        f"runefoble-map-grid-config.ts has {grid_config_lines} lines (target < 140)"
    )
    assert uploader_lines < 120, (
        f"runefoble-map-uploader.ts has {uploader_lines} lines (target < 120)"
    )

    # Custom Element registration checks
    assert "@customElement('runefoble-map-dropzone')" in dropzone_code
    assert "@customElement('runefoble-map-grid-config')" in grid_config_code
    assert "@customElement('runefoble-map-uploader')" in uploader_code

    # Event contract checks
    assert "'upload-start'" in dropzone_code
    assert "'upload-progress'" in dropzone_code
    assert "'upload-success'" in dropzone_code
    assert "'upload-error'" in dropzone_code

    assert "'grid-change'" in grid_config_code
    assert "toggleCellShroud" in grid_config_code
    assert "revealAll" in grid_config_code
    assert "shroudAll" in grid_config_code

    assert "'map-uploaded'" in uploader_code
    assert "runefoble-map-dropzone" in uploader_code
    assert "runefoble-map-grid-config" in uploader_code
    assert "shroud-overlay" in uploader_code
    assert "uploadEndpoint" in uploader_code

    # Index re-exports
    assert "runefoble-map-dropzone" in index_code
    assert "runefoble-map-grid-config" in index_code
    assert "runefoble-map-uploader" in index_code


def test_battlemap_uploader_silo_asset_frontdoor_upload():
    """Verify Silo S3 asset upload frontdoor endpoint integrates with map uploader contract."""
    from gateway_api.main import app as gateway_app

    gateway_client = TestClient(gateway_app)
    sample_png = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06"
        b"\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01"
        b"\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    )

    response = gateway_client.post(
        "/api/v1/assets/upload",
        files={"file": ("underdark_chasm.png", sample_png, "image/png")},
        data={"owner_id": "gm-decomposed", "asset_type": "battlemap"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "asset_id" in data
    assert "battlemaps/" in data["object_key"]
    assert data["content_type"] == "image/png"
    assert data["owner_id"] == "gm-decomposed"
    assert "download_url" in data


def test_battlemap_uploader_storybook_stories_coverage():
    """Verify Storybook stories cover all component visual states."""
    stories_file = (
        REPO_ROOT / "services" / "board_state" / "ui" / "src" / "runefoble-map-uploader.stories.ts"
    )
    assert stories_file.is_file()
    stories_code = stories_file.read_text(encoding="utf-8")
    assert "EmptyDropzone" in stories_code
    assert "UploadingProgress" in stories_code
    assert "AlignedMapPreview" in stories_code
    assert "FogOfWarMasked" in stories_code
