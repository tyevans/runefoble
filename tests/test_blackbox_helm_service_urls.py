"""Blackbox checks for service URL environment variables in the rendered Helm chart.

The tests render the umbrella chart with `helm template` and read only the public
manifest output. They check which container receives each cross-service URL and
which value it gets. They also check the settings that read those names, through the
public `PlatformSettings` model, with no code default.
"""

import shutil
from pathlib import Path

import pytest
import yaml
from runefoble_platform.config import PlatformSettings

from tests.helpers.process import run_command

HELM_CHART = Path("deployments/helm/runefoble")

# Every service URL setting. Each one is read from RUNEFOBLE_<SERVICE>_URL with no default.
SERVICE_URL_SETTINGS: dict[str, str] = {
    "game_session_url": "RUNEFOBLE_GAME_SESSION_URL",
    "board_state_url": "RUNEFOBLE_BOARD_STATE_URL",
    "the_watcher_url": "RUNEFOBLE_WATCHER_URL",
    "character_sheet_url": "RUNEFOBLE_CHARACTER_SHEET_URL",
    "campaign_lore_url": "RUNEFOBLE_CAMPAIGN_LORE_URL",
    "campaign_analytics_url": "RUNEFOBLE_CAMPAIGN_ANALYTICS_URL",
    "soundscape_url": "RUNEFOBLE_SOUNDSCAPE_URL",
    "rules_compendium_url": "RUNEFOBLE_RULES_COMPENDIUM_URL",
    "asset_forge_url": "RUNEFOBLE_ASSET_FORGE_URL",
    "voice_agent_url": "RUNEFOBLE_VOICE_AGENT_URL",
    "audience_studio_url": "RUNEFOBLE_AUDIENCE_STUDIO_URL",
}

# Expected env var -> {container: expected URL}. Each container listed here must carry the
# variable. Every other container must not carry it.
EXPECTED_SERVICE_URLS: dict[str, dict[str, str]] = {
    "RUNEFOBLE_WATCHER_URL": {
        "game-session": "http://the-watcher:8001",
        "voice-agent": "http://the-watcher:8001",
        "gateway-api": "http://the-watcher:8001",
        "gateway-mcp": "http://the-watcher:8001",
    },
    "RUNEFOBLE_VOICE_AGENT_URL": {
        "game-session": "http://voice-agent:8005",
        "gateway-api": "http://voice-agent:8005",
    },
    "RUNEFOBLE_BOARD_STATE_URL": {
        "gateway-api": "http://board-state:8002",
        "gateway-mcp": "http://board-state:8002",
    },
    "RUNEFOBLE_INFERENCE_URL": {
        "the-watcher": "http://inference-worker:8100",
    },
    "RUNEFOBLE_SOUNDSCAPE_URL": {
        "gateway-api": "http://soundscape:8009",
    },
    "RUNEFOBLE_CAMPAIGN_LORE_URL": {
        "gateway-api": "http://campaign-lore:8006",
    },
    "RUNEFOBLE_CAMPAIGN_ANALYTICS_URL": {
        "gateway-api": "http://campaign-analytics:8011",
    },
    "RUNEFOBLE_CHARACTER_SHEET_URL": {
        "game-session": "http://character-sheet:8003",
        "gateway-api": "http://character-sheet:8003",
        "gateway-mcp": "http://character-sheet:8003",
    },
    "RUNEFOBLE_GAME_SESSION_URL": {
        "gateway-api": "http://game-session:8004",
        "gateway-mcp": "http://game-session:8004",
        # Outpost funding debits the stronghold treasury in game_session (TASK-0795).
        "campaign-lore": "http://game-session:8004",
    },
    "RUNEFOBLE_RULES_COMPENDIUM_URL": {
        "gateway-api": "http://rules-compendium:8007",
        "gateway-mcp": "http://rules-compendium:8007",
    },
}


def _render_deployments() -> dict[str, dict]:
    """Render the chart and return every Deployment keyed by its name."""
    if not shutil.which("helm"):
        pytest.skip("helm CLI not available")

    proc = run_command(
        ["helm", "template", "runefoble", str(HELM_CHART)], check=True, timeout=240.0
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


def test_rendered_service_addresses_use_only_runefoble_prefixed_names():
    """Every rendered in-cluster service address is named RUNEFOBLE_*_URL, once per name."""
    env_by_container = _container_env(_render_deployments())

    for container, env in env_by_container.items():
        for env_name, value in env.items():
            if not env_name.endswith("_URL") or not value.startswith("http://"):
                continue
            assert env_name.startswith("RUNEFOBLE_"), (
                f"{container} renders {env_name}; service URLs use the RUNEFOBLE_ prefix"
            )


@pytest.mark.parametrize("field", sorted(SERVICE_URL_SETTINGS))
def test_service_url_setting_has_no_code_default(field, monkeypatch):
    """With its variable unset, each service URL setting is None. No in-cluster default."""
    monkeypatch.delenv(SERVICE_URL_SETTINGS[field], raising=False)

    settings = PlatformSettings(_env_file=None)

    assert getattr(settings, field) is None


@pytest.mark.parametrize(("field", "env_name"), sorted(SERVICE_URL_SETTINGS.items()))
def test_service_url_setting_reads_its_runefoble_name(field, env_name, monkeypatch):
    """Each service URL setting reads its value from RUNEFOBLE_<SERVICE>_URL."""
    monkeypatch.setenv(env_name, "http://service.example:9000")

    settings = PlatformSettings(_env_file=None)

    assert getattr(settings, field) == "http://service.example:9000"
