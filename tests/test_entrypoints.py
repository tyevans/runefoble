"""Comprehensive verification of developer interfaces, CLI entrypoints, and microservices."""

import shutil
import subprocess

import pytest
from fastapi.testclient import TestClient


def test_required_developer_cli_tools_installed():
    """Verify that all prerequisite developer CLI tools are accessible in PATH."""
    import os

    if os.environ.get("RUNEFOBLE_WORKER_HOST") or os.environ.get("RUNEFOBLE_SKIP_DEV_TOOLS"):
        pytest.skip("Skipping developer CLI tool check on worker-only host")

    path = f"{os.path.expanduser('~/.local/bin')}:{os.environ.get('PATH', '')}"
    tools = ["uv", "pnpm", "docker", "helm", "kind", "kubectl"]
    missing = [tool for tool in tools if shutil.which(tool, path=path) is None]
    assert not missing, (
        f"Missing required developer CLI tools: {missing}. Run 'make install-tools'."
    )


@pytest.mark.parametrize(
    "make_target",
    [
        "help",
        "dev",
        "install-tools",
        "helm-lint",
        "helm-template",
        "lint",
        "test-property",
        "dev",
        "dev-api",
        "dev-frontend",
    ],
)
def test_makefile_targets_dry_run(make_target: str):
    """Verify that core Makefile targets parse correctly without syntax or missing variable errors."""
    proc = subprocess.run(
        ["make", "-n", make_target],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, f"Makefile target '{make_target}' failed dry-run: {proc.stderr}"


def test_frontend_storybook_watcher_protection():
    """Verify that Storybook scripts in package.json enable polling to protect against inotify limits."""
    from pathlib import Path

    pkg_json = Path("frontend/package.json").read_text()
    assert "WATCHPACK_POLLING=true" in pkg_json
    assert "CHOKIDAR_USEPOLLING=true" in pkg_json


def test_microservice_entrypoint_initialization():
    """Verify all microservice FastAPI entrypoints initialize and generate OpenAPI schemas."""
    from asset_forge.main import app as forge_app
    from board_state.main import app as board_app
    from character_sheet.main import app as character_app
    from game_session.main import app as session_app
    from gateway_api.main import app as gateway_app
    from inference_worker.api import app as inference_app
    from the_watcher.main import app as watcher_app
    from voice_agent.main import app as voice_app

    apps = [
        ("gateway-api", gateway_app),
        ("the-watcher", watcher_app),
        ("inference-worker", inference_app),
        ("board-state", board_app),
        ("character-sheet", character_app),
        ("game-session", session_app),
        ("voice-agent", voice_app),
        ("asset-forge", forge_app),
    ]

    for name, app in apps:
        client = TestClient(app)
        res = client.get("/healthz")
        assert res.status_code == 200, f"Service '{name}' health check failed: {res.text}"

        openapi_schema = app.openapi()
        assert openapi_schema["info"]["title"], f"Service '{name}' failed to generate OpenAPI info"
        assert len(openapi_schema["paths"]) > 0, f"Service '{name}' has no exposed routes"


def test_mcp_gateway_tool_registry():
    """Verify that the Model Context Protocol (MCP) server registers all required game tools."""
    from gateway_mcp.server import mcp

    # Inspect registered tools on FastMCP server
    registered_tools = [tool.name for tool in mcp._tool_manager.list_tools()]
    expected_tools = [
        "roll_dice",
        "inspect_tactical_board",
        "move_board_token",
        "apply_absentee_penalty",
        "narrate_with_the_watcher",
        "cast_spell",
        "modify_character_hp",
        "add_condition",
        "query_encounter_state",
        "inspect_inventory",
        "create_encounter",
        "execute_agent_action_plan",
    ]

    for tool in expected_tools:
        assert tool in registered_tools, f"MCP tool '{tool}' not registered on FastMCP server"


def test_frontend_container_and_ingress_configuration():
    """Verify frontend Dockerfile, nginx SPA config, and Helm ingress localhost routing."""
    from pathlib import Path

    import yaml

    dockerfile = Path("frontend/Dockerfile")
    assert dockerfile.exists(), "frontend/Dockerfile must exist for cluster deployment"
    assert "nginx:alpine" in dockerfile.read_text()

    nginx_conf = Path("frontend/nginx.conf")
    assert nginx_conf.exists(), "frontend/nginx.conf must exist for SPA routing"
    assert "try_files $uri $uri/ /index.html;" in nginx_conf.read_text()

    values_path = Path("deployments/helm/runefoble/values.yaml")
    values = yaml.safe_load(values_path.read_text())
    hosts = [h["host"] for h in values.get("ingress", {}).get("hosts", [])]
    assert "localhost" in hosts, (
        "Ingress must route 'localhost' to support local curl and browser access"
    )
    assert "runefoble.local" in hosts, "Ingress must route 'runefoble.local'"
