"""Blackbox start-up checks for ADR-0015 (4) and ADR-0013 (manifest contract).

A service that cannot read its UI manifest, or that lacks its Watcher URL or its event
store in a deployed environment, must refuse to start. It must not fall back to canned
data. Each check runs in a child Python process. The UI manifest checks run the module
import. The game_session checks run the app lifespan, which builds the container.
"""

from __future__ import annotations

import os
import shutil
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

from tests.helpers.game_session_startup import STARTED_MARKER, start_game_session
from tests.helpers.ports import free_port
from tests.helpers.process import run_command
from tests.helpers.redis_container import redis_container

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
    return run_command(
        [sys.executable, "-c", f"import {module}"],
        cwd=pythonpath.parent if pythonpath is not None else REPO_ROOT,
        env=env,
        timeout=120,
        check=False,
    )


@pytest.mark.parametrize(
    ("service", "module"),
    [
        ("character_sheet", "character_sheet.main"),
        ("soundscape", "soundscape.main"),
        ("rules_compendium", "rules_compendium.main"),
        ("the_watcher", "the_watcher.main"),
        ("board_state", "board_state.main"),
    ],
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
    [
        "character_sheet.main",
        "soundscape.main",
        "rules_compendium.main",
        "the_watcher.main",
        "board_state.main",
    ],
)
def test_service_starts_when_ui_manifest_is_present(module: str) -> None:
    """With the vendored manifest in place, the same import succeeds."""
    result = _import_module(module, None, {})

    assert result.returncode == 0, result.stderr


@pytest.fixture(scope="module")
def startup_redis_url() -> Iterator[str]:
    """A real Redis for the start-ups that must succeed. The lifespan pings the bus."""
    with redis_container(free_port()) as url:
        yield url


# A deployed game_session needs the Zitadel provisioner token for invite accounts (TASK-0967).
# The tests below check other start-up rules, so each one supplies a token.
PROVISIONER = {"RUNEFOBLE_ZITADEL_SERVICE_TOKEN": "test-provisioner-token"}


def test_game_session_refuses_to_start_in_deployed_mode_without_the_provisioner_token() -> None:
    """A deployed game_session with no Zitadel provisioner token stops at start-up (ADR-0023 c)."""
    result = start_game_session(
        {
            "RUNEFOBLE_ENVIRONMENT": "production",
            "RUNEFOBLE_WATCHER_URL": "http://the-watcher:8001",
            "RUNEFOBLE_ZITADEL_SERVICE_TOKEN": None,
        },
        REPO_ROOT,
    )

    assert result.returncode != 0
    assert "RUNEFOBLE_ZITADEL_SERVICE_TOKEN must be set" in result.stderr
    assert STARTED_MARKER not in result.stdout


def test_game_session_refuses_to_start_in_deployed_mode_without_watcher_url() -> None:
    """RUNEFOBLE_WATCHER_URL unset in staging or production stops game_session at start-up."""
    result = start_game_session(
        {"RUNEFOBLE_ENVIRONMENT": "production", "RUNEFOBLE_WATCHER_URL": None, **PROVISIONER},
        REPO_ROOT,
    )

    assert result.returncode != 0
    assert "RUNEFOBLE_WATCHER_URL must be set" in result.stderr
    assert STARTED_MARKER not in result.stdout


def test_game_session_refuses_to_start_in_deployed_mode_without_a_reachable_event_store() -> None:
    """A deployed game_session whose event store setting names no reachable store stops.

    RUNEFOBLE_DATABASE_URL points at a closed port. The lifespan builds the store before it
    serves, so start-up fails. The memory store is never a substitute (ADR-0015 (f)).
    """
    closed_dsn = f"postgresql+asyncpg://runefoble:runefoble@127.0.0.1:{free_port()}/runefoble"
    result = start_game_session(
        {
            "RUNEFOBLE_ENVIRONMENT": "production",
            **PROVISIONER,
            "RUNEFOBLE_WATCHER_URL": "http://the-watcher:8001",
            "RUNEFOBLE_EVENT_STORE_BACKEND": "postgresql",
            "RUNEFOBLE_DATABASE_URL": closed_dsn,
        },
        REPO_ROOT,
    )

    assert result.returncode != 0
    assert "EventStoreInitializationError" in result.stderr
    assert STARTED_MARKER not in result.stdout


def test_game_session_refuses_the_memory_event_store_in_deployed_mode() -> None:
    """A deployed game_session that selects the memory event store stops at start-up."""
    result = start_game_session(
        {
            "RUNEFOBLE_ENVIRONMENT": "production",
            **PROVISIONER,
            "RUNEFOBLE_WATCHER_URL": "http://the-watcher:8001",
            "RUNEFOBLE_EVENT_STORE_BACKEND": "memory",
        },
        REPO_ROOT,
    )

    assert result.returncode != 0
    assert "memory event store is refused" in result.stderr
    assert STARTED_MARKER not in result.stdout


def test_game_session_starts_in_development_without_watcher_url(startup_redis_url: str) -> None:
    """Development keeps working without a Watcher. Autopilot still refuses per request."""
    result = start_game_session(
        {
            "RUNEFOBLE_ENVIRONMENT": "development",
            "RUNEFOBLE_WATCHER_URL": None,
            "RUNEFOBLE_REDIS_URL": startup_redis_url,
        },
        REPO_ROOT,
    )

    assert result.returncode == 0, result.stderr
    assert STARTED_MARKER in result.stdout


def test_game_session_starts_in_deployed_mode_with_watcher_url(
    postgres_service, startup_redis_url: str
) -> None:
    """A configured Watcher URL satisfies the deployed-mode start-up rule.

    A deployed service also needs its PostgreSQL event store (TASK-0707), so the child
    process gets a reachable database.
    """

    result = start_game_session(
        {
            "RUNEFOBLE_ENVIRONMENT": "production",
            **PROVISIONER,
            "RUNEFOBLE_WATCHER_URL": "http://the-watcher:8001",
            "RUNEFOBLE_EVENT_STORE_BACKEND": "postgresql",
            "RUNEFOBLE_DATABASE_URL": str(postgres_service["dsn"]),
            "RUNEFOBLE_REDIS_URL": startup_redis_url,
        },
        REPO_ROOT,
    )

    assert result.returncode == 0, result.stderr
    assert STARTED_MARKER in result.stdout
