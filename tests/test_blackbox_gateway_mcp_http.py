"""Blackbox tests for the gateway MCP server over streamable HTTP (TASK-0623).

Governed by ADR-0001 (no anonymous mutation, endpoint stays off the public ingress) and
ADR-0005 (Deployment and Service in Helm). Each test starts the public entrypoint, connects
with an MCP client over HTTP, and reads the protocol result. No private state is touched.
"""

from __future__ import annotations

import asyncio
import os
import shutil
import socket
import subprocess
import sys
import time
from collections.abc import Iterator
from pathlib import Path

import pytest
import yaml

from tests.helpers.mcp_http import mcp_session
from tests.test_blackbox_deployability_images import (
    ImageRow,
    build_image,
    docker_daemon_available,
    free_port,
    read_image_table,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
HELM_CHART = REPO_ROOT / "deployments" / "helm" / "runefoble"
GATEWAY_MCP_PORT = 8012

# The static tools documented in docs/reference/fastmcp-gateway.md.
STATIC_TOOLS = {
    "add_condition",
    "apply_absentee_penalty",
    "apply_condition",
    "calculate_encounter_balance",
    "cast_spell",
    "create_encounter",
    "execute_agent_action_plan",
    "get_character_sheet",
    "inspect_inventory",
    "inspect_tactical_board",
    "modify_character_hp",
    "move_board_token",
    "narrate_with_the_watcher",
    "query_encounter_state",
    "query_monster_stat_block",
    "roll_dice",
}

# Upstream URLs that the gateway needs at deploy time. The port is closed on purpose: tool
# listing never calls an upstream service.
UPSTREAM_ENV = {
    "BOARD_STATE_URL": "http://127.0.0.1:9",
    "CHARACTER_SHEET_URL": "http://127.0.0.1:9",
    "GAME_SESSION_URL": "http://127.0.0.1:9",
    "RULES_COMPENDIUM_URL": "http://127.0.0.1:9",
    "THE_WATCHER_URL": "http://127.0.0.1:9",
}


def _wait_for_port(port: int, process: subprocess.Popen | None = None) -> None:
    """Block until a TCP connection to 127.0.0.1:port succeeds, or fail after 60 seconds."""
    deadline = time.monotonic() + 60.0
    while time.monotonic() < deadline:
        if process is not None and process.poll() is not None:
            output = process.stdout.read().decode("utf-8", "replace") if process.stdout else ""
            raise AssertionError(f"gateway-mcp exited early with {process.returncode}:\n{output}")
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                return
        except OSError:
            time.sleep(0.2)
    raise AssertionError(f"nothing listens on 127.0.0.1:{port}")


async def _list_tool_names(endpoint: str) -> set[str]:
    """Initialize an MCP session over HTTP and return the names of the listed tools."""
    async with mcp_session(endpoint) as session:
        listed = await session.list_tools()
    return {tool.name for tool in listed.tools}


def _tool_names_when_ready(endpoint: str) -> set[str]:
    """Retry the MCP handshake until the server answers, or fail after 60 seconds.

    A published container port accepts TCP before the application is ready, so the first
    handshakes can fail. The loop retries the public protocol call only.
    """
    deadline = time.monotonic() + 60.0
    while True:
        try:
            return asyncio.run(_list_tool_names(endpoint))
        except Exception:
            if time.monotonic() > deadline:
                raise
            time.sleep(0.5)


@pytest.fixture
def gateway_process() -> Iterator[str]:
    """Start `python -m gateway_mcp.main` on a free port and yield its MCP endpoint URL."""
    port = free_port()
    env = {
        **os.environ,
        **UPSTREAM_ENV,
        "GATEWAY_MCP_HOST": "127.0.0.1",
        "GATEWAY_MCP_PORT": str(port),
    }
    process = subprocess.Popen(
        [sys.executable, "-m", "gateway_mcp.main"],
        cwd=REPO_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    try:
        _wait_for_port(port, process)
        yield f"http://127.0.0.1:{port}/mcp"
    finally:
        process.terminate()
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=15)


def test_entrypoint_serves_static_tools_over_streamable_http(gateway_process: str):
    """An MCP client initializes over HTTP and lists the 16 static tools."""
    assert _tool_names_when_ready(gateway_process) == STATIC_TOOLS


def test_entrypoint_refuses_to_start_without_upstream_urls():
    """Start-up names a missing upstream URL and exits, so no deployment serves localhost."""
    env = {key: value for key, value in os.environ.items() if key not in UPSTREAM_ENV}
    env["GATEWAY_MCP_PORT"] = str(free_port())
    result = subprocess.run(
        [sys.executable, "-m", "gateway_mcp.main"],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode != 0
    assert "BOARD_STATE_URL" in result.stderr


def _rendered_documents() -> list[dict]:
    if not shutil.which("helm"):
        pytest.skip("helm CLI not available")
    result = subprocess.run(
        ["helm", "template", "runefoble", str(HELM_CHART)],
        capture_output=True,
        text=True,
        check=True,
        timeout=120,
    )
    return [doc for doc in yaml.safe_load_all(result.stdout) if doc]


def test_helm_renders_gateway_mcp_service_on_port_8012_without_ingress():
    """The chart exposes gateway-mcp as a ClusterIP Service only, with no ingress path."""
    documents = _rendered_documents()

    service = next(
        d for d in documents if d["kind"] == "Service" and d["metadata"]["name"] == "gateway-mcp"
    )
    assert service["spec"]["type"] == "ClusterIP"
    assert service["spec"]["ports"][0]["port"] == GATEWAY_MCP_PORT

    deployment = next(
        d for d in documents if d["kind"] == "Deployment" and d["metadata"]["name"] == "gateway-mcp"
    )
    container = deployment["spec"]["template"]["spec"]["containers"][0]
    assert container["ports"][0]["containerPort"] == GATEWAY_MCP_PORT
    assert container["image"].startswith("runefoble/gateway-mcp:")

    env = {item["name"]: item.get("value") for item in container["env"]}
    for key in UPSTREAM_ENV:
        assert env.get(key), f"{key} is not rendered on the gateway-mcp Deployment"
        assert "localhost" not in env[key] and "127.0.0.1" not in env[key]

    for document in documents:
        if document["kind"] != "Ingress":
            continue
        backends = {
            path["backend"]["service"]["name"]
            for rule in document["spec"].get("rules", [])
            for path in rule.get("http", {}).get("paths", [])
        }
        assert "gateway-mcp" not in backends


def _gateway_mcp_row() -> ImageRow:
    (row,) = [r for r in read_image_table() if r.name == "gateway-mcp"]
    return row


@pytest.mark.docker
@pytest.mark.skipif(not docker_daemon_available(), reason="Docker daemon is not reachable")
def test_built_gateway_mcp_image_serves_static_tools_over_streamable_http():
    """The built image starts and an MCP client lists the 16 static tools on port 8012."""
    row = _gateway_mcp_row()
    build_image(row)

    host_port = free_port()
    env_args: list[str] = []
    for key, value in UPSTREAM_ENV.items():
        env_args += ["-e", f"{key}={value}"]
    container = subprocess.run(
        ["docker", "run", "-d", *env_args, "-p", f"127.0.0.1:{host_port}:{row.port}", row.tag],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert container.returncode == 0, f"docker run failed: {container.stderr}"
    container_id = container.stdout.strip()
    try:
        names = _tool_names_when_ready(f"http://127.0.0.1:{host_port}/mcp")
        assert names == STATIC_TOOLS
    finally:
        subprocess.run(["docker", "rm", "-f", container_id], capture_output=True, timeout=120)
