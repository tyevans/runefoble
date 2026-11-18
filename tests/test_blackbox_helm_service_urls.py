"""Blackbox checks for service URL environment variables in the rendered Helm chart.

The tests render the umbrella chart with `helm template` and read only the public
manifest output. They check which container receives each cross-service URL and
which value it gets. Code defaults are checked by running the public module import
in a clean interpreter.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

HELM_CHART = Path("deployments/helm/runefoble")

# Expected env var -> {container: expected URL}. Each container listed here must carry the
# variable. Every other container must not carry it.
EXPECTED_SERVICE_URLS: dict[str, dict[str, str]] = {
    "RUNEFOBLE_WATCHER_URL": {
        "game-session": "http://the-watcher:8001",
        "voice-agent": "http://the-watcher:8001",
        "gateway-api": "http://the-watcher:8001",
    },
    "RUNEFOBLE_VOICE_AGENT_URL": {
        "game-session": "http://voice-agent:8005",
        "gateway-api": "http://voice-agent:8005",
    },
    "RUNEFOBLE_BOARD_STATE_URL": {
        "gateway-api": "http://board-state:8002",
    },
    "RUNEFOBLE_INFERENCE_URL": {
        "the-watcher": "http://inference-worker:8100",
    },
    "SOUNDSCAPE_SERVICE_URL": {
        "gateway-api": "http://soundscape:8009",
    },
    "CAMPAIGN_LORE_URL": {
        "gateway-api": "http://campaign-lore:8006",
    },
    "CAMPAIGN_ANALYTICS_URL": {
        "gateway-api": "http://campaign-analytics:8011",
    },
    "RUNEFOBLE_CHARACTER_SHEET_URL": {
        "game-session": "http://character-sheet:8003",
        "gateway-api": "http://character-sheet:8003",
        "gateway-mcp": "http://character-sheet:8003",
    },
    "RUNEFOBLE_GAME_SESSION_URL": {
        "gateway-api": "http://game-session:8004",
        # Outpost funding debits the stronghold treasury in game_session (TASK-0795).
        "campaign-lore": "http://game-session:8004",
    },
}


def _render_deployments() -> dict[str, dict]:
    """Render the chart and return every Deployment keyed by its name."""
    if not shutil.which("helm"):
        pytest.skip("helm CLI not available")

    proc = subprocess.run(
        ["helm", "template", "runefoble", str(HELM_CHART)],
        capture_output=True,
        text=True,
        check=True,
    )
    docs = [doc for doc in yaml.safe_load_all(proc.stdout) if doc]
    return {doc["metadata"]["name"]: doc for doc in docs if doc.get("kind") == "Deployment"}


def _container_env(deployments: dict[str, dict]) -> dict[str, dict[str, str]]:
    """Return {container name: {env name: env value}} for every container with plain values."""
    result: dict[str, dict[str, str]] = {}
    for deployment in deployments.values():
        containers = deployment["spec"]["template"]["spec"]["containers"]
        for container in containers:
            env = {item["name"]: item.get("value", "") for item in container.get("env", [])}
            result[container["name"]] = env
    return result


def test_each_service_url_renders_on_the_matching_container():
    """Each expected URL key renders on its consumer with the expected in-cluster address."""
    env_by_container = _container_env(_render_deployments())

    for env_name, consumers in EXPECTED_SERVICE_URLS.items():
        for container, expected_url in consumers.items():
            assert container in env_by_container, f"container {container} not rendered"
            actual = env_by_container[container].get(env_name)
            assert actual == expected_url, (
                f"{container} {env_name}: expected {expected_url!r}, got {actual!r}"
            )


def test_service_urls_render_only_on_declared_consumers():
    """No container receives a service URL key it does not consume."""
    env_by_container = _container_env(_render_deployments())

    for env_name, consumers in EXPECTED_SERVICE_URLS.items():
        for container, env in env_by_container.items():
            if container in consumers:
                continue
            assert env_name not in env, f"{container} must not set {env_name}"


def test_service_urls_never_point_at_localhost():
    """No rendered service URL uses localhost or 127.0.0.1."""
    env_by_container = _container_env(_render_deployments())

    for env_name in EXPECTED_SERVICE_URLS:
        for container, env in env_by_container.items():
            value = env.get(env_name)
            if value is None:
                continue
            assert "localhost" not in value and "127.0.0.1" not in value, (
                f"{container} {env_name} points at localhost: {value}"
            )


@pytest.mark.parametrize(
    ("module", "attribute", "env_name", "expected"),
    [
        (
            "voice_agent.dependencies",
            "WATCHER_URL",
            "RUNEFOBLE_WATCHER_URL",
            "http://the-watcher:8001",
        ),
        (
            "runefoble_platform.config",
            "PlatformSettings().soundscape_url",
            "SOUNDSCAPE_SERVICE_URL",
            "http://soundscape:8009",
        ),
    ],
)
def test_code_defaults_match_the_chart(module, attribute, env_name, expected):
    """With the variable unset, the code default matches the in-cluster address."""
    env = {key: value for key, value in os.environ.items() if key != env_name}
    script = f"import {module} as m; print(m.{attribute})"
    proc = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert proc.returncode == 0, f"import failed:\n{proc.stderr}"
    assert proc.stdout.strip() == expected
