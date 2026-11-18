"""Blackbox start-up checks for ADR-0015 (4) and ADR-0013 (manifest contract).

A service that cannot read its UI manifest, or that lacks its Watcher URL in a
deployed environment, must refuse to start. It must not fall back to canned data.
Each check runs the real module import in a child Python process.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


def _import_module(module: str, pythonpath: Path | None, env_overrides: dict[str, str | None]):
    env = {**os.environ}
    for key, value in env_overrides.items():
        if value is None:
            env.pop(key, None)
        else:
            env[key] = value
    if pythonpath is not None:
        env["PYTHONPATH"] = str(pythonpath)
    return subprocess.run(
        [sys.executable, "-c", f"import {module}"],
        cwd=pythonpath.parent if pythonpath is not None else REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


@pytest.mark.parametrize(
    ("service", "module"),
    [("character_sheet", "character_sheet.main"), ("soundscape", "soundscape.main")],
)
def test_service_refuses_to_start_when_ui_manifest_is_missing(
    tmp_path: Path, service: str, module: str
) -> None:
    """A copy of the service package without its ui/ directory fails at import."""
    package_dir = REPO_ROOT / "services" / service / "src" / service
    staged_src = tmp_path / "src"
    shutil.copytree(package_dir, staged_src / service)

    result = _import_module(module, staged_src, {})

    assert result.returncode != 0
    assert "UI manifest not found" in result.stderr
    assert "ui/manifest.json" in result.stderr


@pytest.mark.parametrize(
    "module",
    ["character_sheet.main", "soundscape.main"],
)
def test_service_starts_when_ui_manifest_is_present(module: str) -> None:
    """With the vendored manifest in place, the same import succeeds."""
    result = _import_module(module, None, {})

    assert result.returncode == 0, result.stderr


def test_game_session_refuses_to_start_in_deployed_mode_without_watcher_url() -> None:
    """RUNEFOBLE_WATCHER_URL unset in staging or production stops game_session at start-up."""
    result = _import_module(
        "game_session.main",
        None,
        {"RUNEFOBLE_ENVIRONMENT": "production", "RUNEFOBLE_WATCHER_URL": None},
    )

    assert result.returncode != 0
    assert "RUNEFOBLE_WATCHER_URL must be set" in result.stderr


def test_game_session_starts_in_development_without_watcher_url() -> None:
    """Development keeps working without a Watcher. Autopilot still refuses per request."""
    result = _import_module(
        "game_session.main",
        None,
        {"RUNEFOBLE_ENVIRONMENT": "development", "RUNEFOBLE_WATCHER_URL": None},
    )

    assert result.returncode == 0, result.stderr


def test_game_session_starts_in_deployed_mode_with_watcher_url() -> None:
    """A configured Watcher URL satisfies the deployed-mode start-up rule."""
    result = _import_module(
        "game_session.main",
        None,
        {
            "RUNEFOBLE_ENVIRONMENT": "production",
            "RUNEFOBLE_WATCHER_URL": "http://the-watcher:8001",
        },
    )

    assert result.returncode == 0, result.stderr
