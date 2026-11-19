"""Comprehensive verification of developer interfaces, CLI entrypoints, and microservices."""

import shutil
from contextlib import ExitStack

import pytest
from fastapi.testclient import TestClient

from tests.helpers.mcp_http import listed_tools_sync, serve_mcp
from tests.helpers.process import run_command


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
    proc = run_command(["make", "-n", make_target], timeout=240.0)
    assert proc.returncode == 0, f"Makefile target '{make_target}' failed dry-run: {proc.stderr}"


def test_microservice_entrypoint_initialization(monkeypatch, tmp_path, seam_restorer):
    """Verify all microservice FastAPI entrypoints initialize and generate OpenAPI schemas."""
    from asset_forge.main import app as forge_app
    from board_state.main import app as board_app
    from character_sheet.main import app as character_app
    from gateway_api.main import app as gateway_app
    from inference_worker.api import app as inference_app
    from voice_agent.main import app as voice_app
    from voice_agent.synthesis_engine import get_speech_synthesizer, set_speech_synthesizer

    from tests.helpers.game_session_app import session_app
    from tests.helpers.the_watcher_app import watcher_app

    # The voice agent is ready only when its speech binary answers. A stub stands in for espeak-ng.
    speech_stub = tmp_path / "espeak-ng-version"
    speech_stub.write_text("#!/bin/sh\necho 'eSpeak NG stub'\nexit 0\n", encoding="utf-8")
    speech_stub.chmod(0o755)
    monkeypatch.setenv("RUNEFOBLE_VOICE_TTS_BINARY", str(speech_stub))
    seam_restorer.replace(get_speech_synthesizer, set_speech_synthesizer, None)

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
        with ExitStack() as stack:
            # The gateway builds its upstream clients in its lifespan, and /healthz probes them.
            if name == "gateway-api":
                client = stack.enter_context(TestClient(app))
            else:
                client = TestClient(app)
            res = client.get("/healthz")
        assert res.status_code == 200, f"Service '{name}' health check failed: {res.text}"

        openapi_schema = app.openapi()
        assert openapi_schema["info"]["title"], f"Service '{name}' failed to generate OpenAPI info"
        assert len(openapi_schema["paths"]) > 0, f"Service '{name}' has no exposed routes"


def test_mcp_gateway_tool_registry():
    """Verify that the Model Context Protocol (MCP) server registers all required game tools."""
    # Inspect registered tools on FastMCP server
    with serve_mcp() as endpoint:
        registered_tools = list(listed_tools_sync(endpoint))
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
    assert "nginx:alpine" in dockerfile.read_text()

    nginx_conf = Path("frontend/nginx.conf")
    assert "try_files $uri $uri/ /index.html;" in nginx_conf.read_text()

    values_path = Path("deployments/helm/runefoble/values.yaml")
    values = yaml.safe_load(values_path.read_text())
    hosts = [h["host"] for h in values.get("ingress", {}).get("hosts", [])]
    assert "localhost" in hosts, (
        "Ingress must route 'localhost' to support local curl and browser access"
    )
    assert "runefoble.local" in hosts, "Ingress must route 'runefoble.local'"
