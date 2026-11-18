"""Blackbox checks for ADR-0013 and ADR-0015 (4): each service serves its vendored UI manifest.

GET /ui/manifest returns the parsed content of the service's `ui/manifest.json`. A service
whose manifest is missing does not start.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
from importlib import import_module
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from tests.helpers.process import run_command

REPO_ROOT = Path(__file__).resolve().parents[1]

# (bounded context directory, FastAPI app module) for every service that serves a manifest.
MANIFEST_SERVICES = [
    ("board_state", "board_state.main"),
    ("character_sheet", "character_sheet.main"),
    ("game_session", "game_session.main"),
    ("the_watcher", "the_watcher.main"),
    ("voice_agent", "voice_agent.main"),
    ("campaign_analytics", "campaign_analytics.main"),
    ("asset_forge", "asset_forge.main"),
    ("rules_compendium", "rules_compendium.main"),
    ("campaign_lore", "campaign_lore.main"),
    ("soundscape", "soundscape.main"),
]


def _vendored_manifest(service: str) -> dict:
    path = REPO_ROOT / "services" / service / "ui" / "manifest.json"
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.mark.parametrize(("service", "module"), MANIFEST_SERVICES)
def test_ui_manifest_frontdoor_equals_vendored_file(service: str, module: str) -> None:
    """GET /ui/manifest returns exactly the vendored manifest of the service."""
    app = import_module(module).app
    client = TestClient(app)

    response = client.get("/ui/manifest")

    assert response.status_code == 200
    assert response.json() == _vendored_manifest(service)


@pytest.mark.parametrize(("service", "module"), MANIFEST_SERVICES)
def test_service_refuses_to_start_without_its_ui_manifest(
    tmp_path: Path, service: str, module: str
) -> None:
    """A copy of the service package without its ui/ directory fails at import."""
    package_dir = REPO_ROOT / "services" / service / "src" / service
    staged_src = tmp_path / "src"
    shutil.copytree(package_dir, staged_src / service)

    result = run_command(
        [sys.executable, "-c", f"import {module}"],
        cwd=tmp_path,
        env={**os.environ, "PYTHONPATH": str(staged_src)},
        timeout=120,
        check=False,
    )

    assert result.returncode != 0
    assert "UI manifest not found" in result.stderr
