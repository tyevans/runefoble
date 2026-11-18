"""Blackbox checks for the SpiceDB preshared key (TASK-0625).

The key has one source: the RUNEFOBLE_SPICEDB_PRESHARED_KEY environment variable.
It has no literal default. A process without the key must fail at startup.

Governed by:
- ADR-0001: SpiceDB Zanzibar Object Authorization (the key is an operator secret)
- ADR-0015: Audit Remediation Decisions (decision c and task 0625)
- Hard Invariant 7: Blackbox TDD with Frontdoor Setup
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from uuid import uuid4

import pytest

from tests.helpers.ports import free_port
from tests.helpers.process import run_command

REPO_ROOT = Path(__file__).resolve().parents[1]
KEY_VAR = "RUNEFOBLE_SPICEDB_PRESHARED_KEY"
KEY_VARS = {KEY_VAR, "SPICEDB_TOKEN", "SPICEDB_PRESHARED_KEY"}
SERVICE_DEPENDENCY_MODULES = [
    "rules_compendium.dependencies",
    "asset_forge.dependencies",
    "board_state.dependencies",
    "soundscape.dependencies",
    "the_watcher.dependencies",
    "campaign_lore.dependencies",
]


def _env(**extra: str) -> dict[str, str]:
    """Return the current environment without any preshared key variables."""
    env = {k: v for k, v in os.environ.items() if k not in KEY_VARS}
    env.update(extra)
    return env


def _run_python(code: str, env: dict[str, str], cwd: Path) -> subprocess.CompletedProcess[str]:
    """Run Python code in a fresh interpreter, outside the repo so no .env file loads."""
    return run_command([sys.executable, "-c", code], env=env, cwd=cwd, timeout=180, check=False)


def test_platform_settings_fail_without_key(tmp_path: Path) -> None:
    """Constructing PlatformSettings without the key exits non-zero and names the variable."""
    result = _run_python(
        "from runefoble_platform.config import PlatformSettings; PlatformSettings()",
        _env(),
        tmp_path,
    )
    assert result.returncode != 0
    assert KEY_VAR in result.stderr


@pytest.mark.parametrize("module_name", SERVICE_DEPENDENCY_MODULES)
def test_service_startup_fails_without_key(module_name: str, tmp_path: Path) -> None:
    """Each service dependency module refuses to load when the key is missing."""
    result = _run_python(f"import {module_name}", _env(), tmp_path)
    assert result.returncode != 0
    assert KEY_VAR in result.stderr


def test_rules_compendium_sends_configured_key(tmp_path: Path) -> None:
    """The rules-compendium factory uses the configured key, not the removed 'secret' literal."""
    code = (
        "from rules_compendium.dependencies import get_spicedb_client; "
        "print(get_spicedb_client().token)"
    )
    result = _run_python(code, _env(**{KEY_VAR: "key-from-environment"}), tmp_path)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip().splitlines()[-1] == "key-from-environment"


def test_spicedb_client_requires_key_when_none_is_passed(monkeypatch: pytest.MonkeyPatch) -> None:
    """The auth library refuses to pick a literal key when no token and no environment key exist."""
    from runefoble_auth.spicedb import SpiceDBClient

    monkeypatch.delenv(KEY_VAR, raising=False)
    monkeypatch.delenv("SPICEDB_TOKEN", raising=False)
    with pytest.raises(RuntimeError, match=KEY_VAR):
        SpiceDBClient(endpoint="localhost:1")


def test_audience_studio_config_requires_key(tmp_path: Path) -> None:
    """The audience-studio key reader throws without the key unless NODE_ENV is test."""
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed")
    module = REPO_ROOT / "services" / "audience_studio" / "src" / "config.ts"
    script = (
        f"import {{ readSpicedbPresharedKey }} from '{module.as_posix()}';"
        "readSpicedbPresharedKey(process.env);"
    )
    env = _env()
    env.pop("NODE_ENV", None)
    result = run_command(
        [node, "--experimental-strip-types", "--input-type=module", "-e", script],
        env=env,
        cwd=tmp_path,
        timeout=60,
        check=False,
    )
    assert result.returncode != 0
    assert KEY_VAR in result.stderr


@pytest.mark.skipif(shutil.which("docker") is None, reason="needs Docker for a live SpiceDB")
def test_live_spicedb_enforces_configured_key(tmp_path: Path) -> None:
    """A live SpiceDB that enforces the Helm key accepts the same key from the service factory."""

    key = f"live-key-{uuid4().hex[:8]}"
    port = free_port()
    container = subprocess.check_output(
        [
            "docker",
            "run",
            "-d",
            "--rm",
            "-p",
            f"{port}:50051",
            "authzed/spicedb:v1.34.0",
            "serve",
            "--grpc-preshared-key",
            key,
        ],
        text=True,
        timeout=240.0,
    ).strip()
    try:
        endpoint = f"127.0.0.1:{port}"
        code = (
            "import asyncio\n"
            "from rules_compendium.dependencies import get_spicedb_client\n"
            "async def probe():\n"
            "    client = get_spicedb_client()\n"
            "    await client.write_schema('definition user {}')\n"
            "    assert 'definition user' in await client.read_schema()\n"
            "asyncio.run(probe())\n"
        )
        deadline = time.time() + 60
        ok = None
        while time.time() < deadline:
            env = _env(
                **{KEY_VAR: key, "RUNEFOBLE_SPICEDB_ENDPOINT": endpoint},
            )
            ok = _run_python(code, env, tmp_path)
            if ok.returncode == 0:
                break
            time.sleep(1)
        assert ok is not None
        assert ok.returncode == 0, ok.stderr

        wrong = _run_python(
            code,
            _env(**{KEY_VAR: "wrong-key", "RUNEFOBLE_SPICEDB_ENDPOINT": endpoint}),
            tmp_path,
        )
        assert wrong.returncode != 0
    finally:
        subprocess.run(
            ["docker", "stop", container], capture_output=True, check=False, timeout=240.0
        )
